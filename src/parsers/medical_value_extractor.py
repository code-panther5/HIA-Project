import re

PATTERNS = {
    "hemoglobin": r"(ha?emoglobin|hb)[^\d]{0,15}(\d+\.?\d*)",
    "wbc": r"(wbc|white blood cell)[^\d]{0,15}(\d+\.?\d*)",
    "rbc": r"(rbc|red blood cell)[^\d]{0,15}(\d+\.?\d*)",
    "platelets": r"(platelet)[^\d]{0,15}(\d+\.?\d*)",
    "glucose": r"(glucose|sugar)[^\d]{0,15}(\d+\.?\d*)",
    "creatinine": r"(creatinine)[^\d]{0,15}(\d+\.?\d*)",
    "cholesterol": r"(cholesterol)[^\d]{0,15}(\d+\.?\d*)",
}


def extract_values(text: str) -> dict:
    """Extract medical lab values from raw report text"""
    if not text:
        return {}

    text = text.lower()
    results = {}

    for key, pattern in PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            try:
                results[key] = float(match.group(2))
            except:
                pass

    return results