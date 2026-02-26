import streamlit as st

class ContextManager:
    """Manages medical report context across the application."""
    
    REPORT_TAG_START = "__REPORT_TEXT__\n"
    REPORT_TAG_END = "\n__END_REPORT_TEXT__"

    @staticmethod
    def get_report_context(messages=None):
        """
        Retrieve report text from session state or message history.
        
        Args:
            messages: Optional list of chat messages to search through
            
        Returns:
            str: The extracted report text or an empty string
        """
        # 1. Try session state first (fastest)
        context_text = st.session_state.get("current_report_text", "")
        if context_text:
            return context_text

        # 2. Try to extract from provided messages (system messages)
        if messages:
            for msg in messages:
                if msg.get("role") == "system" and ContextManager.REPORT_TAG_START in msg.get("content", ""):
                    content = msg.get("content", "")
                    start_idx = content.find(ContextManager.REPORT_TAG_START) + len(ContextManager.REPORT_TAG_START)
                    end_idx = content.find(ContextManager.REPORT_TAG_END)
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        context_text = content[start_idx:end_idx]
                        # Cache in session state
                        st.session_state.current_report_text = context_text
                        return context_text

        return ""

    @staticmethod
    def format_report_for_system(report_text):
        """Format report text with tags for storage in system messages."""
        return f"{ContextManager.REPORT_TAG_START}{report_text}{ContextManager.REPORT_TAG_END}"
