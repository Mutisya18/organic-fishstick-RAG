"""
RAG-Specific Logging Helpers

Provides structured log builders for RAG pipeline events:
- Retrieval metadata (chunks, scores, sources)
- Generation context (tokens, latency, prompts)
- Quality metrics (groundedness, citations)
- Security flags (PII, content moderation)
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from utils.logger.session_manager import SessionManager
from utils.logger.pii import scrub_text, scrub_dict


class RAGLogger:
    """Centralized RAG logging utilities."""
    
    def __init__(self):
        self.sm = SessionManager()
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request/trace ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_prompt(prompt: str) -> str:
        """Hash a prompt for logging (IP protection)."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def log_retrieval(
        self,
        request_id: str,
        query: str,
        top_k: int,
        chunks: List[Dict[str, Any]],
        similarity_scores: List[float],
        source_documents: List[str],
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Log vector database retrieval metadata.
        
        Args:
            request_id: Unique request identifier.
            query: User query (will be scrubbed for PII).
            top_k: Number of chunks requested.
            chunks: List of retrieved chunks with metadata.
            similarity_scores: Relevance scores for each chunk.
            source_documents: List of source file names/URLs.
            latency_ms: Time taken to retrieve (optional).
        """
        # Scrub query for PII
        query_scrubbed, query_flagged = scrub_text(query)
        
        # Extract chunk IDs
        chunk_ids = [c.get("id", f"chunk_{i}") for i, c in enumerate(chunks)]
        
        entry = {
            "event": "retrieval_complete",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "retrieval_metadata": {
                "top_k": top_k,
                "retrieved_count": len(chunks),
                "chunk_ids": chunk_ids,
                "similarity_scores": similarity_scores,
                "source_documents": source_documents,
            },
            "query_metadata": {
                "query_summary": query_scrubbed[:100] if query_scrubbed else "",
                "query_pii_flagged": query_flagged,
            },
            "latency_ms": latency_ms,
        }
        
        self.sm.log(entry, severity="INFO")
    
    def log_generation(
        self,
        request_id: str,
        query: str,
        response: str,
        prompt_template_version: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: Optional[float] = None,
        groundedness_score: Optional[float] = None,
        cited_chunks: Optional[List[str]] = None,
    ) -> None:
        """
        Log LLM generation metadata.
        
        Args:
            request_id: Unique request identifier (links to retrieval).
            query: User query.
            response: LLM response (will be scrubbed for PII).
            prompt_template_version: Version of system prompt used.
            prompt_tokens: Input token count.
            completion_tokens: Output token count.
            latency_ms: Time taken to generate (optional).
            groundedness_score: 0.0-1.0 self-assessment of answer groundedness.
            cited_chunks: List of chunk IDs actually cited in response.
        """
        # Scrub query and response for PII
        query_scrubbed, query_flagged = scrub_text(query)
        response_scrubbed, response_flagged = scrub_text(response)
        
        total_tokens = prompt_tokens + completion_tokens
        
        entry = {
            "event": "generation_complete",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "generation_metadata": {
                "prompt_hash": self.hash_prompt(""),  # System prompt hash (protect IP)
                "prompt_template_version": prompt_template_version,
                "tokens": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
            },
            "quality_metrics": {
                "groundedness_score": groundedness_score,
                "cited_chunks": cited_chunks or [],
            },
            "query_metadata": {
                "query_summary": query_scrubbed[:100] if query_scrubbed else "",
                "query_pii_flagged": query_flagged,
            },
            "response_metadata": {
                "response_summary": response_scrubbed[:100] if response_scrubbed else "",
                "response_pii_flagged": response_flagged,
            },
            "latency_ms": latency_ms,
        }
        
        self.sm.log(entry, severity="INFO")
    
    def log_end_to_end_rag(
        self,
        request_id: str,
        query: str,
        response: str,
        retrieval_metadata: Dict[str, Any],
        generation_metadata: Dict[str, Any],
        total_latency_ms: Optional[float] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a complete end-to-end RAG interaction.
        
        Args:
            request_id: Unique request identifier.
            query: User query.
            response: Final response.
            retrieval_metadata: Dict with top_k, chunk_ids, similarity_scores, source_documents.
            generation_metadata: Dict with prompt_template_version, tokens, latency_ms.
            total_latency_ms: Total E2E latency (optional).
            quality_metrics: Dict with groundedness_score, cited_chunks, user_feedback.
        """
        query_scrubbed, query_flagged = scrub_text(query)
        response_scrubbed, response_flagged = scrub_text(response)
        
        entry = {
            "event": "rag_interaction_complete",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "retrieval": retrieval_metadata,
            "generation": generation_metadata,
            "quality": quality_metrics or {},
            "query_summary": query_scrubbed[:100] if query_scrubbed else "",
            "response_summary": response_scrubbed[:100] if response_scrubbed else "",
            "pii_flags": {
                "query_pii_detected": query_flagged,
                "response_pii_detected": response_flagged,
            },
            "total_latency_ms": total_latency_ms,
        }
        
        self.sm.log(entry, severity="INFO")
    
    def log_api_request(
        self,
        request_id: str,
        api_name: str,
        endpoint: str,
        method: str,
        request_body: Dict[str, Any],
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Log external API request (OpenAI, Vector DB, etc.).
        
        Args:
            request_id: Unique request identifier.
            api_name: Name of API (e.g., "openai_embeddings", "pinecone_query").
            endpoint: Full URL endpoint.
            method: HTTP method (GET, POST, etc.).
            request_body: Full request payload.
            latency_ms: Time taken (optional).
        """
        entry = {
            "event": "api_request",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "api": {
                "name": api_name,
                "endpoint": endpoint,
                "method": method,
                "request_body": str(request_body)[:1000],  # Truncate if too long
            },
            "latency_ms": latency_ms,
        }
        
        self.sm.log(entry, severity="DEBUG")
    
    def log_api_response(
        self,
        request_id: str,
        api_name: str,
        status_code: int,
        response_headers: Dict[str, str],
        response_body: Dict[str, Any],
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Log external API response.
        
        Args:
            request_id: Unique request identifier.
            api_name: Name of API.
            status_code: HTTP status code.
            response_headers: Response headers.
            response_body: Full response payload.
            latency_ms: Time taken (optional).
        """
        entry = {
            "event": "api_response",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "api": {
                "name": api_name,
                "status_code": status_code,
                "response_headers": dict(response_headers),
                "response_body": str(response_body)[:1000],  # Truncate if too long
            },
            "latency_ms": latency_ms,
        }
        
        severity = "WARNING" if status_code >= 400 else "DEBUG"
        self.sm.log(entry, severity=severity)
    
    def log_warning(
        self,
        request_id: str,
        message: str,
        event_type: str = "warning",
    ) -> None:
        """
        Log a warning event (e.g., empty retrieval, low confidence).
        
        Args:
            request_id: Unique request identifier.
            message: Warning message.
            event_type: Type of warning (e.g., "empty_retrieval", "low_confidence").
        """
        entry = {
            "event": event_type,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "message": message,
        }
        
        self.sm.log(entry, severity="WARNING")
    
    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        traceback_str: Optional[str] = None,
    ) -> None:
        """
        Log an error event (API timeout, model failure, etc.).
        
        Args:
            request_id: Unique request identifier.
            error_type: Type of error.
            error_message: Error message (will be scrubbed for PII).
            traceback_str: Full traceback (optional).
        """
        msg_scrubbed, _ = scrub_text(error_message)
        tb_scrubbed = None
        if traceback_str:
            tb_scrubbed, _ = scrub_text(traceback_str)
        
        entry = {
            "event": "error",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "error": {
                "type": error_type,
                "message": msg_scrubbed,
                "traceback": tb_scrubbed,
            },
        }
        
        self.sm.log(entry, severity="ERROR")
    
    def log(
        self,
        request_id: str,
        event: str,
        severity: str = "INFO",
        message: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Generic log method for arbitrary events.
        
        Args:
            request_id: Unique request identifier.
            event: Event type/name.
            severity: Log severity (DEBUG, INFO, WARNING, ERROR).
            message: Optional message.
            context: Optional context dictionary with additional fields.
        """
        entry = {
            "event": event,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
        }
        
        if message:
            entry["message"] = message
        
        if context:
            entry.update(context)
        
        self.sm.log(entry, severity=severity)


# Global singleton instance
_rag_logger = RAGLogger()
