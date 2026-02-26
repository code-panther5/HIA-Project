import pytest
from unittest.mock import MagicMock
from utils.pdf_extractor import table_to_medical_text, extract_text_from_pdf

def test_table_to_medical_text_basic():
    """Test standard table conversion without keyword filtering."""
    # A table row that used to be ignored because it didn't have specific keywords
    tables = [[
        ["ALT (SGPT)", "45", "U/L", "Up to 40"],
        ["AST (SGOT)", "38", "U/L", "Up to 40"]
    ]]
    
    result = table_to_medical_text(tables)
    
    assert "ALT (SGPT): 45 U/L (Ref: Up to 40)" in result
    assert "AST (SGOT): 38 U/L (Ref: Up to 40)" in result

def test_table_to_medical_text_empty_rows():
    """Test handling of empty or None rows."""
    tables = [[
        [None, None, None, None],
        ["Glucose", "100", "mg/dL", "70-110"]
    ]]
    
    result = table_to_medical_text(tables)
    assert "Glucose: 100 mg/dL (Ref: 70-110)" in result
    assert "None:" not in result

def test_extract_text_from_pdf_fallback(mock_pdfplumber, mocker):
    """Test fallback to raw text if no tables are found."""
    # Mock validation to pass
    mocker.patch('utils.pdf_extractor.validate_pdf_file', return_value=(True, None))
    mocker.patch('utils.pdf_extractor.validate_pdf_content', return_value=(True, None))
    
    # Mock PDF page with no tables but some text
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = []
    mock_page.extract_text.return_value = "Raw medical report text"
    
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdfplumber.return_value = mock_pdf
    
    result = extract_text_from_pdf("dummy.pdf")
    assert result == "Raw medical report text"
