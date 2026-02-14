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
import json
from typing import Optional, Dict, Any, Tuple

from rag.query_data import extract_sources_from_query
from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager
from rag.config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION
from backend.chat import run_chat
from eligibility.orchestrator import EligibilityOrchestrator
from database import db as database_manager
from utils.commands import parse_command, validate_command_args, get_registry, get_validation_error_tooltip, dispatch_command
from database.initialization import print_database_error_guide


# Initialize logging
rag_logger = RAGLogger()
session_manager = SessionManager()

# Initialize database (lazy: actual connection happens on first use)
try:
    database_manager.initialize(debug=False)
    database_available = True
except Exception as e:
    rag_logger.log_error(
        request_id="startup",
        error_type="DatabaseInitError",
        error_message=f"Database module failed to initialize: {str(e)}",
        traceback_str=traceback.format_exc(),
    )
    database_available = False
    print_database_error_guide()

# Initialize eligibility orchestrator (will raise if config/data files missing)
try:
    eligibility_orchestrator = EligibilityOrchestrator()
    eligibility_available = True
except Exception as e:
    rag_logger.log_error(
        request_id="startup",
        error_type="EligibilityInitError",
        error_message=f"Eligibility module failed to initialize: {str(e)}",
        traceback_str=traceback.format_exc(),
    )
    eligibility_available = False


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = session_manager._session_id
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None


def validate_message_can_send(message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message can be sent (for command mode: block send until required args provided).

    Returns:
        (can_send, error_tooltip). If can_send is False, error_tooltip is the message to show.
    """
    parsed = parse_command(message)
    if not parsed.is_command:
        return True, None
    if parsed.parse_errors:
        return False, parsed.parse_errors[0] if parsed.parse_errors else "Invalid command."
    registry = get_registry()
    if parsed.command_name not in registry.get("_by_command", {}):
        return False, "I don't recognize that command."
    tooltip = get_validation_error_tooltip(parsed.command_name, parsed.args_raw, registry)
    if tooltip:
        return False, tooltip
    return True, None


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
    
    # Check database availability
    if not database_available:
        st.error(
            "❌ **Database System Unavailable**\n\n"
            "The chat history system is not responding. "
            "Please check the logs or contact support.\n\n"
            "**Troubleshooting:**\n"
            "1. Check if database service is running\n"
            "2. Verify DATABASE_TYPE and DATABASE_URL in .env\n"
            "3. Check logs directory for detailed errors\n"
        )
        st.stop()
    
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
            - Eligibility checking {'✅' if eligibility_available else '❌ (unavailable)'}
            """
        )
        st.divider()
        if st.button("Clear Chat History"):
            # Archive current conversation if it exists
            if st.session_state.conversation_id is not None:
                try:
                    database_manager.archive_conversation(st.session_state.conversation_id)
                except Exception as e:
                    rag_logger.log_error(
                        request_id="session_cleanup",
                        error_type="ConversationArchiveError",
                        error_message=f"Failed to archive conversation: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )
            # Reset session state for new conversation
            st.session_state.chat_history = []
            st.session_state.conversation_id = None
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
        # Block send when a command requires args (e.g. /check_eligibility needs account number)
        can_send, send_error_tooltip = validate_message_can_send(user_input)
        if not can_send and send_error_tooltip:
            st.error(send_error_tooltip)
            # Do not add to history or process
        else:
            # Create conversation on first message if needed
            if st.session_state.conversation_id is None:
                try:
                    conv = database_manager.create_conversation(
                        user_id="default_user",
                        title=f"Chat Session {st.session_state.session_id[:8]}"
                    )
                    st.session_state.conversation_id = conv['id']
                    rag_logger.log_warning(
                        request_id="session_init",
                        message=f"Created new conversation: {st.session_state.conversation_id}",
                        event_type="conversation_created",
                    )
                    print(f"[DEBUG] Created conversation: {st.session_state.conversation_id}")
                except Exception as e:
                    rag_logger.log_error(
                        request_id="session_init",
                        error_type="ConversationCreationError",
                        error_message=f"Failed to create conversation: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )
                    st.error("Failed to create chat session. Please refresh and try again.")
                    st.stop()
            
            # Add user message to history immediately
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input,
                "metadata": None,
            })
            
            # Render user message
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Process query via shared backend (context + RAG/eligibility)
            with st.spinner("🔍 Searching and generating response..."):
                result = run_chat(
                    user_input,
                    st.session_state.conversation_id,
                    database_manager,
                    prompt_version=prompt_version,
                )
            
            if result["success"]:
                # Save user message to database
                try:
                    print(f"[DEBUG] Saving user message to conversation: {st.session_state.conversation_id}")
                    database_manager.save_user_message(
                        conversation_id=st.session_state.conversation_id,
                        content=user_input,
                        request_id=result["request_id"]
                    )
                except Exception as e:
                    rag_logger.log_error(
                        request_id=result["request_id"],
                        error_type="UserMessageSaveError",
                        error_message=f"Failed to save user message: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )
                
                # Display success response
                with st.chat_message("assistant"):
                    st.markdown(result["response"])
                    
                    # Show sources and details in single expander
                    if result["is_eligibility_flow"]:
                        # For eligibility flow, show raw payload in expander
                        with st.expander("📋 Eligibility Details"):
                            st.json(result["eligibility_payload"])
                            st.divider()
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Request ID", result["request_id"][:8] + "...")
                            with col2:
                                st.metric("Latency", f"{result['latency_ms']:.2f} ms")
                    else:
                        # For RAG flow, show sources and details
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
                assistant_metadata = {
                    "request_id": result["request_id"],
                    "latency_ms": result["latency_ms"],
                    "source": "eligibility" if result["is_eligibility_flow"] else "rag",
                }
                
                if result["is_eligibility_flow"]:
                    assistant_metadata["eligibility_payload"] = result["eligibility_payload"]
                else:
                    assistant_metadata["sources"] = result["sources"]
                    assistant_metadata["prompt_version"] = result["prompt_version"]
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result["response"],
                    "metadata": assistant_metadata,
                })
                
                # Save assistant message to database
                try:
                    database_manager.save_assistant_message(
                        conversation_id=st.session_state.conversation_id,
                        content=result["response"],
                        request_id=result["request_id"],
                        metadata={
                            "latency_ms": result["latency_ms"],
                            "source": "eligibility" if result["is_eligibility_flow"] else "rag",
                        }
                    )
                except Exception as e:
                    rag_logger.log_error(
                        request_id=result["request_id"],
                        error_type="AssistantMessageSaveError",
                        error_message=f"Failed to save assistant message: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )
            
            else:
                # Save user message to database (before showing error)
                try:
                    print(f"[DEBUG] Saving user message (error case) to conversation: {st.session_state.conversation_id}")
                    database_manager.save_user_message(
                        conversation_id=st.session_state.conversation_id,
                        content=user_input,
                        request_id=result["request_id"]
                    )
                except Exception as e:
                    rag_logger.log_error(
                        request_id=result["request_id"],
                        error_type="UserMessageSaveError",
                        error_message=f"Failed to save user message: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )
                
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
                
                # Save error message to database
                try:
                    database_manager.save_assistant_message(
                        conversation_id=st.session_state.conversation_id,
                        content=f"⚠️ {error_message}",
                        request_id=result["request_id"],
                        metadata={
                            "error_type": result["error_type"],
                            "source": "error"
                        }
                    )
                except Exception as e:
                    rag_logger.log_error(
                        request_id=result["request_id"],
                        error_type="ErrorMessageSaveError",
                        error_message=f"Failed to save error message: {str(e)}",
                        traceback_str=traceback.format_exc(),
                    )


if __name__ == "__main__":
    main()
