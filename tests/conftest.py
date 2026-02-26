import pytest
from unittest.mock import MagicMock
import sys
import os

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def mock_streamlit(mocker):
    """Mock streamlit session state and secrets."""
    mock_st = mocker.patch('streamlit.session_state', {}, create=True)
    mocker.patch('streamlit.secrets', {}, create=True)
    mocker.patch('streamlit.error')
    mocker.patch('streamlit.success')
    mocker.patch('streamlit.info')
    mocker.patch('streamlit.warning')
    return mock_st

@pytest.fixture
def mock_pdfplumber(mocker):
    """Mock pdfplumber for PDF extraction tests."""
    return mocker.patch('pdfplumber.open')
