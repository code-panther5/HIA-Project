import streamlit as st
import logging
from agents.analysis_agent import AnalysisAgent
from utils.context_manager import ContextManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_analysis_state():
    """Initialize analysis-related session state variables."""
    if "analysis_agent" not in st.session_state:
        st.session_state.analysis_agent = AnalysisAgent()

    if "chat_agent" not in st.session_state:
        try:
            from agents.chat_agent import ChatAgent

            # Check if GROQ_API_KEY exists before initializing
            if "GROQ_API_KEY" not in st.secrets:
                st.session_state.chat_agent = None
                st.session_state.chat_agent_error = "GROQ_API_KEY not found in secrets. Please add it to .streamlit/secrets.toml"
            else:
                st.session_state.chat_agent = ChatAgent()
                st.session_state.chat_agent_error = None
        except (KeyError, ImportError, Exception) as e:
            st.session_state.chat_agent = None
            import traceback
            error_details = traceback.format_exc()
            st.session_state.chat_agent_error = f"Failed to initialize chat agent: {str(e)}\n\nDetails: {error_details[:500]}"
            logger.error(f"Chat agent initialization failed: {str(e)}")


def check_rate_limit():
    init_analysis_state()
    return st.session_state.analysis_agent.check_rate_limit()


def generate_analysis(data, system_prompt, check_only=False, session_id=None):
    """Generate analysis if within rate limits."""
    logger.info("AI Service called for analysis generation")

    init_analysis_state()

    if check_only:
        logger.info("Rate limit check only requested")
        return st.session_state.analysis_agent.check_rate_limit()

    logger.info("Sending data to Analysis Agent")
    result = st.session_state.analysis_agent.analyze_report(
        data=data, system_prompt=system_prompt, check_only=False
    )

    if isinstance(result, dict) and result.get("success"):
        logger.info("AI analysis generated successfully")
    else:
        logger.error(f"AI analysis generation failed: {result.get('error') if isinstance(result, dict) else result}")

    return result


def get_chat_response(query, context_text, chat_history):
    """Get response from the chat agent with automatic context retrieval."""
    init_analysis_state()

    if st.session_state.chat_agent is None:
        error_msg = st.session_state.get(
            "chat_agent_error",
            "Chat functionality is currently unavailable.",
        )
        return f"Error: {error_msg}"

    # Automatically retrieve context if not provided
    if not context_text and chat_history:
        context_text = ContextManager.get_report_context(chat_history)

        if not context_text:
            # Fallback for old sessions: try assistant responses
            for msg in reversed(chat_history):
                if msg["role"] == "assistant" and len(msg.get("content", "")) > 100:
                    context_text = msg["content"][:5000]
                    break

    if not context_text:
        context_text = "No report context available. Relying on chat history only."

    # Handle Vector Store initialization
    if "vector_store" not in st.session_state or st.session_state.get(
        "vector_store_key"
    ) != len(context_text):
        try:
            with st.spinner("Processing context..."):
                st.session_state.vector_store = (
                    st.session_state.chat_agent.initialize_vector_store(context_text)
                )
                st.session_state.vector_store_key = len(context_text)
        except Exception as e:
            logger.warning(f"Could not create vector store: {str(e)}")
            st.warning(f"Could not create vector store: {str(e)}. Using chat history only.")
            try:
                st.session_state.vector_store = (
                    st.session_state.chat_agent.initialize_vector_store("No report context available.")
                )
                st.session_state.vector_store_key = 0
            except Exception:
                return f"Error: Could not initialize vector store. {str(e)}"

    return st.session_state.chat_agent.get_response(
        query, st.session_state.vector_store, chat_history
    )


