import pytest
import streamlit as st
from utils.context_manager import ContextManager

def test_get_report_context_from_session(mock_streamlit):
    """Test retrieving context from session state."""
    st.session_state["current_report_text"] = "Sample Report Content"
    
    result = ContextManager.get_report_context()
    assert result == "Sample Report Content"

def test_get_report_context_from_messages(mock_streamlit):
    """Test extracting context from system messages using tags."""
    st.session_state.clear()
    
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "system", "content": f"Some prefix {ContextManager.REPORT_TAG_START}Hidden Report{ContextManager.REPORT_TAG_END} Some suffix"}
    ]
    
    result = ContextManager.get_report_context(messages)
    assert result == "Hidden Report"
    # Ensure it cached it in session state
    assert st.session_state["current_report_text"] == "Hidden Report"

def test_format_report_for_system():
    """Test formatting report with tags."""
    report = "My Data"
    formatted = ContextManager.format_report_for_system(report)
    assert f"__REPORT_TEXT__\n{report}\n__END_REPORT_TEXT__" == formatted
