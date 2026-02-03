import argparse
import time
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

# Add parent directory to path to import modules from root
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.get_embedding_function import get_embedding_function, OLLAMA_BASE_URL
from utils.logger.rag_logging import RAGLogger
from utils.logger.trace import technical_trace
from rag.config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION
from utils.context.conversation_memory import ConversationMemory

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
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
    
    Args:
        query_text: User's query.
    
    Returns:
        List of source document metadata.
    """
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    docs = db.similarity_search_with_score(query_text, k=5)
    
    sources = []
    for idx, (doc, score) in enumerate(docs):
        sources.append({
            "id": doc.metadata.get("id", f"chunk_{idx}"),
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "N/A"),
            "content_preview": doc.page_content[:100] + "...",
            "similarity_score": float(score),
        })
    
    return sources


@technical_trace
def query_rag(query_text: str, prompt_version: str = DEFAULT_PROMPT_VERSION, conversation_memory: Optional[ConversationMemory] = None) -> str:
    request_id = rag_logger.generate_request_id()
    retrieval_start = time.time()
    
    try:
        # Prepare the DB.
        embedding_function = get_embedding_function()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        # Search the DB.
        results = db.similarity_search_with_score(query_text, k=5)
        retrieval_latency = (time.time() - retrieval_start) * 1000

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

        # Get system prompt based on version
        system_prompt = SYSTEM_PROMPTS.get(prompt_version, SYSTEM_PROMPTS[DEFAULT_PROMPT_VERSION])
        
        # Build context
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        
        # Build conversation context if memory is provided
        conversation_context = ""
        if conversation_memory:
            conversation_context = conversation_memory.get_context()
        
        # Build prompt text
        prompt_parts = [system_prompt]
        
        if conversation_context:
            prompt_parts.append(f"\n\n---Previous Conversation---\n{conversation_context}\n\n---Current Question---")
        
        prompt_parts.append(f"\nContext:\n{context_text}\n\nQuestion: {query_text}")
        prompt = "".join(prompt_parts)
        
        # Generate response
        generation_start = time.time()
        model = OllamaLLM(model="llama3.2:3b", base_url=OLLAMA_BASE_URL)
        response_text = model.invoke(prompt)
        generation_latency = (time.time() - generation_start) * 1000
        
        # Log generation (simplified token count)
        estimated_prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
        estimated_completion_tokens = len(response_text.split()) * 1.3
        
        rag_logger.log_generation(
            request_id=request_id,
            query=query_text,
            response=response_text,
            prompt_template_version=prompt_version,
            prompt_tokens=int(estimated_prompt_tokens),
            completion_tokens=int(estimated_completion_tokens),
            latency_ms=generation_latency,
            groundedness_score=0.85,  # Placeholder
            cited_chunks=chunk_ids,
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
