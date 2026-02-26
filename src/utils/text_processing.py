def clean_cell(cell):
    """Clean table cell text"""
    if not cell:
        return ""
    return str(cell).replace("\n", " ").strip()
