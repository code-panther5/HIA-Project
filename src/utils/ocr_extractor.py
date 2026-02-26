import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_bytes


def preprocess_image(pil_image):
    """Optimized preprocessing for medical lab reports"""
    img = np.array(pil_image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=20)

    # Remove noise
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Adaptive threshold (important!)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )

    return thresh


def extract_text_ocr(pdf_file):
    """
    OCR tuned for medical tables
    """
    try:
        # Reset file pointer just in case
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()
        if len(pdf_bytes) == 0:
            return "OCR failed: Empty PDF bytes"

        images = convert_from_bytes(pdf_bytes, dpi=300)

        full_text = ""

        # Tesseract configuration for tables + numbers
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'

        for img in images:
            processed = preprocess_image(img)

            text = pytesseract.image_to_string(
                processed,
                config=custom_config
            )

            full_text += text + "\n"

        if not full_text.strip():
            return None

        return full_text

    except Exception as e:
        return f"OCR failed: {str(e)}"