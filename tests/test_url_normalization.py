import pytest
from urllib.parse import urljoin

def test_urljoin():
    base = "https://www.hsa.gov.sg/therapeutic-products/guidance-documents"
    rel = "/therapeutic-products/guidance-documents/abc"
    assert urljoin(base, rel) == "https://www.hsa.gov.sg/therapeutic-products/guidance-documents/abc"
    rel2 = "guidance-documents/xyz"
    assert urljoin(base, rel2) == "https://www.hsa.gov.sg/therapeutic-products/guidance-documents/xyz"
