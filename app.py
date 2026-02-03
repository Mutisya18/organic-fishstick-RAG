"""
Streamlit Web UI for RAG Chatbot

Provides a web-based chat interface with:
- Structured logging following RAG logging rules
- Session management with unique request IDs
- Clear, user-friendly error messages
- Chat history display
- Token and latency tracking
"""

import streamlit as st
import time
import traceback
from typing import Optional, Dict, Any

from query_data import query_rag, extract_sources_from_query
from logger.rag_logging import RAGLogger
from logger.session_manager import SessionManager
from config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION


# Initialize logging
rag_logger = RAGLogger()
session_manager = SessionManager()


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = session_manager._session_id
    if "error_message" not in st.session_state:
        st.session_state.error_message = None


def get_user_friendly_error_message(error_type: str, error_message: str) -> str:
    """
    Convert technical errors to user-friendly messages.
    
    Args:
        error_type: Type of exception.
        error_message: Raw error message.
    
    Returns:
        User-friendly error message.
    """
    error_map = {
        "ConnectionError": "Unable to connect to the RAG service. Please check your network and try again.",
        "TimeoutError": "The request timed out. The service is taking too long to respond. Please try again.",
        "ValueError": "Invalid input or configuration. Please try again with a different query.",
        "KeyError": "A required resource is missing. This may indicate a configuration issue.",
        "FileNotFoundError": "A required file is missing. Please ensure the RAG database is initialized.",
        "RuntimeError": "An internal error occurred. Please try again or contact support.",
        "Exception": "An unexpected error occurred. Please try again.",
    }
    
    return error_map.get(error_type, error_message or "An unknown error occurred. Please try again.")


def process_query(query_text: str, prompt_version: str = DEFAULT_PROMPT_VERSION) -> Dict[str, Any]:
    """
    Process user query through RAG pipeline.
    
    Args:
        query_text: User's query string.
        prompt_version: System prompt version to use.
    
    Returns:
        Dictionary with response, error status, metadata, and sources.
    """
    request_id = rag_logger.generate_request_id()
    start_time = time.time()
    
    result = {
        "request_id": request_id,
        "success": False,
        "response": None,
        "error": None,
        "error_type": None,
        "latency_ms": 0,
        "sources": [],
        "prompt_version": prompt_version,
    }
    
    try:
        # Extract sources
        sources = extract_sources_from_query(query_text)
        result["sources"] = sources
        
        # Call RAG query function with prompt version
        response = query_rag(query_text, prompt_version=prompt_version)
        result["success"] = True
        result["response"] = response
        result["latency_ms"] = (time.time() - start_time) * 1000
        
        rag_logger.log_warning(
            request_id=request_id,
            message=f"UI query processed successfully in {result['latency_ms']:.2f}ms",
            event_type="ui_query_complete",
        )
        
    except ConnectionError as e:
        result["error_type"] = "ConnectionError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="ConnectionError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except TimeoutError as e:
        result["error_type"] = "TimeoutError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="TimeoutError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except ValueError as e:
        result["error_type"] = "ValueError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="ValueError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except FileNotFoundError as e:
        result["error_type"] = "FileNotFoundError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="FileNotFoundError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except KeyError as e:
        result["error_type"] = "KeyError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="KeyError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except RuntimeError as e:
        result["error_type"] = "RuntimeError"
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type="RuntimeError",
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    except Exception as e:
        result["error_type"] = type(e).__name__
        result["error"] = str(e)
        rag_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback_str=traceback.format_exc(),
        )
    
    return result


def render_chat_message(role: str, content: str, metadata: Optional[Dict] = None):
    """
    Render a chat message in the UI.
    
    Args:
        role: "user" or "assistant".
        content: Message content.
        metadata: Optional metadata (request_id, latency, etc.).
    """
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            if metadata:
                with st.expander("📊 Details"):
                    if "request_id" in metadata:
                        st.code(f"Request ID: {metadata['request_id']}", language="text")
                    if "latency_ms" in metadata:
                        st.metric("Latency", f"{metadata['latency_ms']:.2f} ms")


def main():
    """Main Streamlit app."""
    
    # Page config
    st.set_page_config(
        page_title="RAG Chatbot",
        page_icon="🤖",
        layout="wide",
    )
    
    # Title and description
    st.title("🤖 Chatbot")
    st.markdown(
        """
        Ask me anything about Digital Lending.
        I'll search relevant information and provide you with accurate answers.
        """
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar config
    with st.sidebar:
        st.header("⚙️ Settings")
        prompt_version = st.selectbox(
            "Prompt Version",
            options=list(SYSTEM_PROMPTS.keys()),
            help="V1.0.0: Fast & simple | V1.1.0: Structured & production-quality"
        )
        st.divider()
        st.header("ℹ️ About")
        st.markdown(
            f"""
            **Session ID**: `{st.session_state.session_id}`
            
            **Features**:
            - Real-time document search
            - Citation tracking
            - Query logging
            - Error handling
            """
        )
        st.divider()
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Display chat history
    for message in st.session_state.chat_history:
        render_chat_message(
            role=message["role"],
            content=message["content"],
            metadata=message.get("metadata"),
        )
    
    # Chat input
    user_input = st.chat_input("Type your question here...")
    
    if user_input:
        # Add user message to history immediately
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "metadata": None,
        })
        
        # Render user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Process query with selected prompt version
        with st.spinner("🔍 Searching and generating response..."):
            result = process_query(user_input, prompt_version=prompt_version)
        
        if result["success"]:
            # Display success response
            with st.chat_message("assistant"):
                st.markdown(result["response"])
                
                # Show sources and details in single expander
                with st.expander("📚 Sources & Details"):
                    # Display sources
                    st.markdown("**Sources Used:**")
                    for idx, source in enumerate(result["sources"], 1):
                        st.markdown(f"**{idx}. {source['source']}**")
                        st.caption(f"Page: {source['page']}")
                        st.caption(f"Preview: {source['content_preview']}")
                    
                    # Divider between sources and details
                    st.divider()
                    
                    # Display technical details as footnote
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Request ID", result["request_id"][:8] + "...")
                    with col2:
                        st.metric("Latency", f"{result['latency_ms']:.2f} ms")
                    with col3:
                        st.metric("Prompt Version", result["prompt_version"])
            
            # Add assistant message to history with sources
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["response"],
                "metadata": {
                    "request_id": result["request_id"],
                    "latency_ms": result["latency_ms"],
                    "sources": result["sources"],
                    "prompt_version": result["prompt_version"],
                },
            })
        
        else:
            # Display error message
            error_message = get_user_friendly_error_message(
                result["error_type"],
                result["error"],
            )
            with st.chat_message("assistant"):
                st.error(f"⚠️ {error_message}")
                with st.expander("🔧 Technical Details"):
                    st.code(f"Error Type: {result['error_type']}\n\n{result['error']}", language="text")
            
            # Add error message to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"⚠️ {error_message}",
                "metadata": {
                    "request_id": result["request_id"],
                    "error_type": result["error_type"],
                },
            })


if __name__ == "__main__":
    main()
