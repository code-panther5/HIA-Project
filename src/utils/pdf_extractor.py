import pdfplumber
from utils.text_processing import clean_cell
from config.app_config import MAX_PDF_PAGES
from utils.validators import validate_pdf_file, validate_pdf_content


def table_to_medical_text(tables):
    """Convert lab tables into readable medical format without strict keyword filtering."""
    lines = []

    for table in tables:
        for row in table:
            # Clean cells and filter out empty rows
            row = [clean_cell(c) for c in row if c is not None]
            
            # Skip if row is effectively empty
            if not any(row):
                continue

            # We assume a medical row has at least a Name and a Value
            if len(row) >= 2:
                test = row[0]
                value = row[1]
                unit = row[2] if len(row) > 2 else ""
                ref = row[3] if len(row) > 3 else ""

                # Less restrictive check: keep it if "test" looks like a name and "value" isn't empty
                if test.strip() and value.strip():
                    lines.append(f"{test}: {value} {unit} (Ref: {ref})".strip())

    return "\n".join(lines)


def extract_text_from_pdf(pdf_file):
    """Extract structured medical data from PDF with raw text fallback."""
    try:
        is_valid, error = validate_pdf_file(pdf_file)
        if not is_valid:
            return False, error

        structured_text = ""
        raw_text = ""

        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                return False, f"PDF exceeds maximum page limit of {MAX_PDF_PAGES}"

            for page in pdf.pages:
                # Try structured extraction first
                tables = page.extract_tables()
                if tables:
                    structured_text += table_to_medical_text(tables) + "\n"
                
                # Also collect raw text as fallback
                try:
                    raw_text += page.extract_text() or ""
                except:
                    pass

        # If structured extraction failed to find anything, use raw text but trim it
        final_text = structured_text.strip()
        if not final_text:
            # Simple heuristic: Use raw text if tables failed
            final_text = raw_text.strip()

        # FINAL FALLBACK: If still no text (likely scanned PDF), try OCR
        if not final_text:
            print("PDFPLUMBER FAILED, TRYING OCR FALLBACK...")
            from utils.ocr_extractor import extract_text_ocr
            # Reset file pointer for OCR
            pdf_file.seek(0)
            ocr_text = extract_text_ocr(pdf_file)
            if ocr_text and not (isinstance(ocr_text, str) and ("error" in ocr_text.lower() or "failed" in ocr_text.lower())):
                print(f"OCR SUCCESSFUL, EXTRACTED {len(ocr_text)} CHARS")
                final_text = ocr_text
            else:
                print(f"OCR FAILED: {ocr_text}")

        if not final_text:
            return False, "No text could be extracted from the report. Please ensure the PDF is clear and contains medical data."

        is_valid, error = validate_pdf_content(final_text)
        if not is_valid:
            print(f"VALIDATION FAILED: {error}")
            return False, error

        return True, final_text

    except Exception as e:
        import traceback
        print(f"FATAL ERROR IN EXTRACTION: {str(e)}\n{traceback.format_exc()}")
        return False, f"Error extracting text from PDF: {str(e)}"

