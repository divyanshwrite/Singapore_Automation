import hashlib

def test_md5_dedup():
    data1 = b"hello world"
    data2 = b"hello world"
    data3 = b"goodbye"
    assert hashlib.md5(data1).hexdigest() == hashlib.md5(data2).hexdigest()
    assert hashlib.md5(data1).hexdigest() != hashlib.md5(data3).hexdigest()
