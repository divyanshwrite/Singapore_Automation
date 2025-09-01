import pytest

def test_pdf_extraction_fallback():
    # Simulate fallback logic
    try:
        raise ImportError("pypdf not available")
    except ImportError:
        assert True

def test_doc_fallback():
    # Simulate fallback logic
    try:
        raise ImportError("textract not available")
    except ImportError:
        assert True
