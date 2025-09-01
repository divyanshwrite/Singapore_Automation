import pytest
import vcr
import httpx
from config import START_URLS

@vcr.use_cassette('tests/vcr_hsa.yaml', record_mode='once')
def test_guidance_page_live():
    url = START_URLS["Therapeutic Products"]
    resp = httpx.get(url)
    assert resp.status_code == 200
    assert "guidance" in resp.text.lower()
