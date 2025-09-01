import pytest
from datetime import datetime

def test_sg_date_parsing():
    date_str = "01 September 2025"
    dt = datetime.strptime(date_str, "%d %B %Y")
    assert dt.year == 2025 and dt.month == 9 and dt.day == 1
