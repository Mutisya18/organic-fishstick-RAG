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
from typing import Optional, Dict, Any

from rag.query_data import query_rag, extract_sources_from_query
from utils.logger.rag_logging import RAGLogger
from utils.logger.session_manager import SessionManager
from utils.context.context_builder import build_rag_context
from rag.config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION
from eligibility.orchestrator import EligibilityOrchestrator
from database import db as database_manager
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


def _get_reason_friendly_title(reason_code: str) -> str:
    """
    Map reason code to friendly display title.
    
    Args:
        reason_code: Internal reason code.
    
    Returns:
        Friendly display title.
    """
    title_map = {
        "JOINT_ACCOUNT_EXCLUSION": "Joint Account Status",
        "AVERAGE_BALANCE_EXCLUSION": "Average Balance",
        "DPD_ARREARS_EXCLUSION": "DPD Arrears",
        "ELMA_EXCLUSION": "ELMA Eligibility",
        "MANDATE_EXCLUSION": "Mandate/Signing Authority",
        "CLASSIFICATION_EXCLUSION": "Customer Classification",
        "LINKED_BASE_EXCLUSION": "Linked Base Account",
        "CUSTOMER_VINTAGE_EXCLUSION": "Customer Vintage",
        "DORMANCY_INACTIVE_EXCLUSION": "Account Activity Status",
        "TURNOVER_EXCLUSION": "Customer Turnover",
        "RECENCY_EXCLUSION": "Recent Banking Patterns"
    }
    return title_map.get(reason_code, reason_code)


def _substitute_evidence_placeholders(template: str, evidence: Dict[str, Any]) -> str:
    """
    Substitute placeholders in evidence template with actual values.
    
    Args:
        template: Template string with {field_name} placeholders.
        evidence: Dictionary with field values.
    
    Returns:
        Formatted string with substituted values.
    """
    result = template
    for key, value in evidence.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))
    return result


def _build_inline_evidence(reason_code: str, evidence: Dict[str, Any], evidence_display_rules: Dict[str, Any]) -> str:
    """
    Build inline evidence string using evidence display rules.
    
    Args:
        reason_code: Internal reason code.
        evidence: Evidence dictionary from reason object.
        evidence_display_rules: Configuration for evidence display.
    
    Returns:
        Formatted inline evidence string (empty if no evidence).
    """
    display_rules = evidence_display_rules.get("display_rules", {})
    rule = display_rules.get(reason_code, {})
    
    # If no evidence exists, return empty string
    if rule.get("has_evidence") is False:
        return ""
    
    # Get format template
    format_template = rule.get("format_template", [])
    if not format_template:
        return ""
    
    # Check for required fields
    required_fields = rule.get("required_fields", [])
    for field in required_fields:
        if field not in evidence or evidence[field] is None or evidence[field] == "":
            return rule.get("missing_error", "Evidence unavailable")
    
    # Build evidence parts using template
    evidence_parts = []
    for template in format_template:
        formatted = _substitute_evidence_placeholders(template, evidence)
        if formatted and formatted.strip():
            evidence_parts.append(formatted)
    
    # Join with " – " for compact inline display
    return " – ".join(evidence_parts)


def format_eligibility_response(payload: Dict[str, Any]) -> str:
    """
    Format eligibility payload into v1.1 compliant UI output.
    
    Implements structured, scannable layout with:
    - Account headers (Customer Name, Account Number, Status)
    - Numbered reasons in order received
    - Inline evidence next to reason titles
    - Per-reason next steps
    - Proper separations per v1.1 spec
    
    Args:
        payload: Eligibility payload from orchestrator.
    
    Returns:
        Formatted markdown string (v1.1 compliant).
    """
    # Load evidence display rules
    try:
        from eligibility.config_loader import ConfigLoader
        config_loader = ConfigLoader()
        evidence_display_rules = config_loader.get_evidence_display_rules()
    except Exception:
        evidence_display_rules = {"display_rules": {}}
    
    response_lines = []
    accounts = payload.get("accounts", [])
    
    if not accounts:
        return "No accounts found in results."
    
    for account_idx, account in enumerate(accounts):
        # ===== ACCOUNT HEADER =====
        customer_name = account.get("customer_name", "Unknown")
        account_number = account.get("account_number", "Unknown")
        status = account.get("status", "UNKNOWN")
        
        response_lines.append(f"Customer Name: {customer_name}")
        response_lines.append("")
        response_lines.append(f"Account Number: {account_number}")
        response_lines.append("")
        response_lines.append(f"Status: {status}")
        response_lines.append("")
        
        # ===== REASONS SECTION =====
        reasons = account.get("reasons", [])
        
        if not reasons:
            # No reasons - account is ELIGIBLE or CANNOT_CONFIRM
            if status == "ELIGIBLE":
                response_lines.append("✅ Customer is eligible for loan limit.")
            elif status == "CANNOT_CONFIRM":
                response_lines.append("Account not found in eligibility database.")
            response_lines.append("")
        else:
            # Render Reasons header
            response_lines.append("Reasons")
            response_lines.append("---")
            
            # Render each reason
            for reason_idx, reason in enumerate(reasons):
                reason_number = reason_idx + 1
                reason_code = reason.get("code", "UNKNOWN")
                
                # Build title with inline evidence
                friendly_title = _get_reason_friendly_title(reason_code)
                evidence = reason.get("evidence", {})
                inline_evidence = _build_inline_evidence(
                    reason_code,
                    evidence,
                    evidence_display_rules
                )
                
                # Format title line
                if inline_evidence:
                    response_lines.append(f"{reason_number}. {friendly_title} ({inline_evidence})")
                else:
                    response_lines.append(f"{reason_number}. {friendly_title}")
                
                # Add meaning
                meaning = reason.get("meaning", "")
                if meaning:
                    response_lines.append(meaning)
                
                # Add next steps
                next_steps = reason.get("next_steps", [])
                if next_steps:
                    response_lines.append("")
                    response_lines.append("Next Steps")
                    for step in next_steps:
                        action = step.get("action", "")
                        owner = step.get("owner", "")
                        if owner:
                            response_lines.append(f"- {action} (Owner: {owner})")
                        else:
                            response_lines.append(f"- {action}")
                
                # Add separator between reasons
                if reason_idx < len(reasons) - 1:
                    response_lines.append("---")
                
                response_lines.append("")
        
        # ===== ACCOUNT SEPARATOR =====
        if account_idx < len(accounts) - 1:
            response_lines.append("==================== NEXT ACCOUNT ====================")
            response_lines.append("")
    
    return "\n".join(response_lines)


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


def process_query(
    query_text: str,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    enriched_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process user query through RAG pipeline.
    
    Args:
        query_text: User's query string.
        prompt_version: System prompt version to use.
        enriched_context: Optional dict with conversation context (system_prompt, context, user_message).
    
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
        "is_eligibility_flow": False,
        "eligibility_payload": None,
    }
    
    # Check if this is an eligibility question
    if eligibility_available:
        try:
            eligibility_payload = eligibility_orchestrator.process_message(query_text)
            if eligibility_payload:
                result["is_eligibility_flow"] = True
                result["eligibility_payload"] = eligibility_payload
                rag_logger.log_warning(
                    request_id=request_id,
                    message="Eligibility flow triggered",
                    event_type="eligibility_detected",
                )
                # For eligibility flow, format the response as readable text
                response_text = format_eligibility_response(eligibility_payload)
                result["success"] = True
                result["response"] = response_text
                result["latency_ms"] = (time.time() - start_time) * 1000
                return result
        except Exception as e:
            # Log eligibility error but continue with RAG
            rag_logger.log_error(
                request_id=request_id,
                error_type="EligibilityProcessError",
                error_message=str(e),
                traceback_str=traceback.format_exc(),
            )
            # Fall through to normal RAG query
    
    try:
        # Extract sources
        sources = extract_sources_from_query(query_text)
        result["sources"] = sources
        
        # Call RAG query function with prompt version and enriched context
        response = query_rag(
            query_text,
            prompt_version=prompt_version,
            enriched_context=enriched_context
        )
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
        
        # Build enriched context from conversation history
        enriched_context = build_rag_context(
            conversation_id=st.session_state.conversation_id,
            user_message=user_input,
            db_manager=database_manager,
            prompt_version=prompt_version
        )
        
        # Process query with selected prompt version and context
        with st.spinner("🔍 Searching and generating response..."):
            result = process_query(
                user_input,
                prompt_version=prompt_version,
                enriched_context=enriched_context
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
