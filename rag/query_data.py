import argparse
import time
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

# Add parent directory to path to import modules from root
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.get_embedding_function import get_embedding_function
from rag.get_generation_function import get_generation_function
from rag.config.provider_config import (
    ACTIVE_EMBEDDING_PROVIDER,
    ACTIVE_GENERATION_PROVIDER,
    DEBUG_MODE,
)
from rag.config.index_registry import (
    get_collection_name_for_provider,
    get_embedding_space_id,
    get_chroma_path_for_provider,
    validate_embedding_space_match,
)
from utils.logger.rag_logging import RAGLogger
from utils.logger.trace import technical_trace
from rag.config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION

rag_logger = RAGLogger()


def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    query_rag(query_text)


def extract_sources_from_query(query_text: str) -> List[Dict[str, Any]]:
    """
    Extract source documents for a query.
    
    Uses the active embedding provider and its corresponding collection.
    
    Args:
        query_text: User's query.
    
    Returns:
        List of source document metadata.
    """
    # Get provider configuration
    embedding_provider = ACTIVE_EMBEDDING_PROVIDER
    collection_name = get_collection_name_for_provider(embedding_provider)
    chroma_path = get_chroma_path_for_provider(embedding_provider)
    
    if DEBUG_MODE:
        print(f"[QUERY] extract_sources using provider: {embedding_provider}")
        print(f"[QUERY]   collection: {collection_name}")
        print(f"[QUERY]   chroma_path: {chroma_path}")
    
    # Get embeddings and database
    embedding_function = get_embedding_function()
    db = Chroma(
        persist_directory=chroma_path,
        collection_name=collection_name,
        embedding_function=embedding_function
    )
    docs = db.similarity_search_with_score(query_text, k=5)
    
    sources = []
    for idx, (doc, score) in enumerate(docs):
        sources.append({
            "id": doc.metadata.get("id", f"chunk_{idx}"),
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "N/A"),
            "content_preview": doc.page_content[:100] + "...",
            "similarity_score": float(score),
            "embedding_space_id": doc.metadata.get("embedding_space_id", "unknown"),
        })
    
    return sources


@technical_trace
def query_rag(
    query_text: str,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    enriched_context: Optional[Dict[str, str]] = None
) -> str:
    """
    Query the RAG system using the configured embedding and generation providers.
    
    Routes to the correct Chroma collection based on active embedding provider,
    generates responses using the configured generation provider, and logs all
    provider information for observability.
    
    Args:
        query_text: The user's question
        prompt_version: System prompt version to use
        enriched_context: Optional context dict with 'system_prompt' and 'context' keys
    
    Returns:
        Generated response text
    """
    request_id = rag_logger.generate_request_id()
    retrieval_start = time.time()
    
    try:
        # ====================================================================
        # RETRIEVAL PHASE
        # ====================================================================
        
        # Get active embedding provider configuration
        embedding_provider = ACTIVE_EMBEDDING_PROVIDER
        collection_name = get_collection_name_for_provider(embedding_provider)
        chroma_path = get_chroma_path_for_provider(embedding_provider)
        embedding_space_id = get_embedding_space_id(embedding_provider)
        
        if DEBUG_MODE:
            print(f"[RETRIEVAL] Provider: {embedding_provider}")
            print(f"[RETRIEVAL] Collection: {collection_name}")
            print(f"[RETRIEVAL] Chroma path: {chroma_path}")
            print(f"[RETRIEVAL] Embedding space: {embedding_space_id}")
        
        # Prepare the DB with provider-specific collection
        embedding_function = get_embedding_function()
        db = Chroma(
            persist_directory=chroma_path,
            collection_name=collection_name,
            embedding_function=embedding_function
        )

        # Search the DB
        results = db.similarity_search_with_score(query_text, k=5)
        retrieval_latency = (time.time() - retrieval_start) * 1000

        # Validate embedding space consistency (safety check)
        for idx, (doc, _score) in enumerate(results):
            doc_space_id = doc.metadata.get("embedding_space_id", "unknown")
            if doc_space_id != embedding_space_id:
                raise ValueError(
                    f"Embedding space mismatch in retrieved document {idx}! "
                    f"Expected: {embedding_space_id}, Got: {doc_space_id}. "
                    f"This indicates mixed embedding spaces in the collection."
                )

        # Log retrieval
        chunk_ids = [doc.metadata.get("id", f"chunk_{i}") for i, (doc, _score) in enumerate(results)]
        similarity_scores = [float(score) for _doc, score in results]
        source_docs = [doc.metadata.get("source", "unknown") for doc, _score in results]
        
        rag_logger.log_retrieval(
            request_id=request_id,
            query=query_text,
            top_k=5,
            chunks=[{"id": cid, "text": doc.page_content} for cid, (doc, _) in zip(chunk_ids, results)],
            similarity_scores=similarity_scores,
            source_documents=source_docs,
            latency_ms=retrieval_latency,
        )

        # ====================================================================
        # GENERATION PHASE
        # ====================================================================
        
        # Get system prompt (from enriched context if provided, else from config)
        if enriched_context:
            system_prompt = enriched_context.get("system_prompt", SYSTEM_PROMPTS.get(prompt_version, SYSTEM_PROMPTS[DEFAULT_PROMPT_VERSION]))
        else:
            system_prompt = SYSTEM_PROMPTS.get(prompt_version, SYSTEM_PROMPTS[DEFAULT_PROMPT_VERSION])
        
        # Build retrieval context from search results
        retrieval_context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        
        # Build prompt text
        prompt_parts = [system_prompt]
        
        # Add conversation context if provided
        if enriched_context and enriched_context.get("context"):
            prompt_parts.append(f"\n\nPrevious conversation:\n{enriched_context['context']}")
        
        # Add retrieval context and current question
        prompt_parts.append(f"\n\nContext:\n{retrieval_context_text}\n\nQuestion: {query_text}")
        prompt = "".join(prompt_parts)
        
        # Get generation provider
        generation_provider = get_generation_function()
        generation_provider_name = ACTIVE_GENERATION_PROVIDER
        
        if DEBUG_MODE:
            gen_info = generation_provider.get_info()
            print(f"[GENERATION] Provider: {generation_provider_name}")
            print(f"[GENERATION] Model: {gen_info.get('model')}")
        
        # Generate response
        generation_start = time.time()
        result = generation_provider.generate(
            prompt=prompt,
            system_instruction=system_prompt
        )
        
        response_text = result["text"]
        usage = result["usage"]
        generation_latency = result["latency_ms"]
        
        # Log generation with provider info
        rag_logger.log_generation(
            request_id=request_id,
            query=query_text,
            response=response_text,
            prompt_template_version=prompt_version,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            latency_ms=generation_latency,
            groundedness_score=0.85,  # Placeholder
            cited_chunks=chunk_ids,
        )
        
        # Log provider information for observability
        rag_logger.log_warning(
            request_id=request_id,
            message=f"RAG completed with {embedding_provider} embeddings and {generation_provider_name} generation",
            event_type="rag_query_complete",
        )

        sources = [doc.metadata.get("id", None) for doc, _score in results]
        formatted_response = f"Response: {response_text}\nSources: {sources}"
        print(formatted_response)
        return response_text
    
    except Exception as e:
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise


if __name__ == "__main__":
    main()
