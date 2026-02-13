import argparse
import os
import shutil
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from sys import path as sys_path

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import modules from root
sys_path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.get_embedding_function import get_embedding_function
from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    DATA_PATH,
    DEBUG_MODE,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_embedding_space_id,
    get_chroma_path_for_provider,
)
from langchain_chroma import Chroma
from utils.logger.rag_logging import RAGLogger
from utils.logger.trace import technical_trace

rag_logger = RAGLogger()


def main():

    # Check if the database should be cleared (using the --clear flag).
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    if args.reset:
        print("✨ Clearing Database")
        clear_database()

    # Create (or update) the data store.
    documents = load_documents()
    chunks = split_documents(documents)
    add_to_chroma(chunks)


@technical_trace
def load_documents():
    request_id = rag_logger.generate_request_id()
    try:
        start_time = time.time()
        docs = []
        data_path = Path(DATA_PATH)
        
        # Load PDF documents
        pdf_docs = load_pdf_documents(data_path)
        docs.extend(pdf_docs)
        
        # Load DOCX documents
        docx_docs = load_docx_documents(data_path)
        docs.extend(docx_docs)
        
        latency = (time.time() - start_time) * 1000
        
        rag_logger.log_warning(
            request_id=request_id,
            message=f"Loaded {len(docs)} documents from {DATA_PATH}",
            event_type="documents_loaded",
        )
        return docs
    except Exception as e:
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=f"Failed to load documents: {str(e)}",
        )
        raise


def load_pdf_documents(data_path: Path):
    try:
        pdf_loader = PyPDFDirectoryLoader(str(data_path))
        pdf_docs = pdf_loader.load()
        if pdf_docs:
            rag_logger.log_warning(
                request_id=rag_logger.generate_request_id(),
                message=f"Loaded {len(pdf_docs)} PDF documents",
                event_type="pdf_documents_loaded",
            )
        return pdf_docs
    except Exception as e:
        rag_logger.log_error(
            request_id=rag_logger.generate_request_id(),
            error_type=type(e).__name__,
            error_message=f"Failed to load PDF documents: {str(e)}",
        )
        return []


def load_docx_documents(data_path: Path):
    docx_docs = []
    try:
        for docx_file in data_path.glob("*.docx"):
            try:
                docx_loader = Docx2txtLoader(str(docx_file))
                docs = docx_loader.load()
                docx_docs.extend(docs)
            except Exception as e:
                rag_logger.log_error(
                    request_id=rag_logger.generate_request_id(),
                    error_type=type(e).__name__,
                    error_message=f"Failed to load DOCX file {docx_file.name}: {str(e)}",
                )
        
        if docx_docs:
            rag_logger.log_warning(
                request_id=rag_logger.generate_request_id(),
                message=f"Loaded {len(docx_docs)} DOCX documents",
                event_type="docx_documents_loaded",
            )
        return docx_docs
    except Exception as e:
        rag_logger.log_error(
            request_id=rag_logger.generate_request_id(),
            error_type=type(e).__name__,
            error_message=f"Failed to load DOCX documents: {str(e)}",
        )
        return []


@technical_trace
def split_documents(documents: list[Document]):
    request_id = rag_logger.generate_request_id()
    try:
        start_time = time.time()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=80,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(documents)
        latency = (time.time() - start_time) * 1000
        
        rag_logger.log_warning(
            request_id=request_id,
            message=f"Split {len(documents)} documents into {len(chunks)} chunks",
            event_type="documents_split",
        )
        return chunks
    except Exception as e:
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=f"Failed to split documents: {str(e)}",
        )
        raise


@technical_trace
def add_to_chroma(chunks: list[Document]):
    """
    Add documents to Chroma vector database.
    
    Routes to the correct provider-specific collection based on configuration.
    Adds embedding_space_id to chunk metadata to prevent mixed-space errors.
    """
    request_id = rag_logger.generate_request_id()
    try:
        # Get the active embedding provider configuration
        embedding_provider = ACTIVE_EMBEDDING_PROVIDER
        collection_name = get_collection_name_for_provider(embedding_provider)
        chroma_path = get_chroma_path_for_provider(embedding_provider)
        embedding_space_id = get_embedding_space_id(embedding_provider)
        
        if DEBUG_MODE:
            print(f"[INGEST] Active embedding provider: {embedding_provider}")
            print(f"[INGEST] Collection name: {collection_name}")
            print(f"[INGEST] Chroma path: {chroma_path}")
            print(f"[INGEST] Embedding space ID: {embedding_space_id}")
        
        # Load the embedding function
        embedding_function = get_embedding_function()
        
        # Load the existing database for this collection
        db = Chroma(
            persist_directory=chroma_path,
            collection_name=collection_name,
            embedding_function=embedding_function
        )

        # Calculate Page IDs and add embedding_space_id to metadata
        chunks_with_ids = calculate_chunk_ids(chunks, embedding_space_id)

        # Add or Update the documents.
        existing_items = db.get(include=[])  # IDs are always included by default
        existing_ids = set(existing_items["ids"])
        print(f"Number of existing documents in collection '{collection_name}': {len(existing_ids)}")

        # Only add documents that don't exist in the DB.
        new_chunks = []
        for chunk in chunks_with_ids:
            if chunk.metadata["id"] not in existing_ids:
                new_chunks.append(chunk)

        if len(new_chunks):
            print(f"👉 Adding new documents to '{collection_name}': {len(new_chunks)}")
            new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
            
            # Process documents in batches to avoid timeout issues with ngrok
            batch_size = 10
            for i in range(0, len(new_chunks), batch_size):
                batch_end = min(i + batch_size, len(new_chunks))
                batch = new_chunks[i:batch_end]
                batch_ids = new_chunk_ids[i:batch_end]
                batch_num = i//batch_size + 1
                print(f"  Processing batch {batch_num}: documents {i+1}-{batch_end}")
                
                try:
                    if DEBUG_MODE:
                        print(f"[DIAGNOSTIC] Attempting to add {len(batch)} documents to Chroma...")
                        print(f"[DIAGNOSTIC] First batch item content length: {len(batch[0].page_content)}")
                        print(f"[DIAGNOSTIC] First batch item metadata: {batch[0].metadata}")
                    db.add_documents(batch, ids=batch_ids)
                    if DEBUG_MODE:
                        print(f"[DIAGNOSTIC] Successfully added batch {batch_num}")
                except Exception as e:
                    print(f"[DIAGNOSTIC] Error in batch {batch_num}: {type(e).__name__}")
                    print(f"[DIAGNOSTIC] Error details: {str(e)}")
                    print(f"[DIAGNOSTIC] First batch item being processed: {batch[0].metadata.get('id', 'UNKNOWN')}")
                    raise
                time.sleep(1)  # Brief pause between batches to prevent overwhelming the server
            
            rag_logger.log_warning(
                request_id=request_id,
                message=f"Added {len(new_chunks)} new documents to Chroma DB (provider: {embedding_provider}, collection: {collection_name})",
                event_type="documents_added_to_db",
            )
        else:
            print("✅ No new documents to add")
            rag_logger.log_warning(
                request_id=request_id,
                message="No new documents to add to DB",
                event_type="no_new_documents",
            )
    except Exception as e:
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=f"Failed to add documents to Chroma: {str(e)}",
        )
        raise


def calculate_chunk_ids(chunks, embedding_space_id: str):
    """
    Calculate unique IDs for chunks and add embedding space metadata.
    
    Creates IDs like "data/monopoly.pdf:6:2" (Source:Page:ChunkIndex)
    Adds embedding_space_id to metadata to detect mixed embedding spaces.
    
    Args:
        chunks: List of Document chunks
        embedding_space_id: The unique identifier for the active embedding space
    
    Returns:
        List of chunks with 'id' and 'embedding_space_id' in metadata
    """
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add metadata
        chunk.metadata["id"] = chunk_id
        chunk.metadata["embedding_space_id"] = embedding_space_id

    return chunks


def clear_database():
    """
    Clear the Chroma database for the active embedding provider.
    
    Only deletes the collection directory for the currently configured provider,
    leaving other provider collections intact for A/B testing.
    """
    chroma_path = get_chroma_path_for_provider(ACTIVE_EMBEDDING_PROVIDER)
    if os.path.exists(chroma_path):
        print(f"🗑️  Clearing Chroma database at: {chroma_path}")
        shutil.rmtree(chroma_path)
        print(f"✅ Cleared database for provider: {ACTIVE_EMBEDDING_PROVIDER}")
    else:
        print(f"ℹ️  No database found at: {chroma_path}")


if __name__ == "__main__":
    main()
