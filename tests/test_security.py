import pytest
from app.security import InvalidURL, RateLimiter, validate_url


@pytest.mark.parametrize("u", [
    "file:///etc/passwd", "ftp://tiktok.com/x", "http://127.0.0.1/",
    "http://localhost/", "https://evil.com/", "https://tiktok.com.evil.com/",
    "https://user:pw@tiktok.com/", "http://169.254.169.254/", "", "x" * 3000,
])
def test_rejects(u):
    with pytest.raises(InvalidURL):
        validate_url(u, resolve=False)


def test_accepts():
    assert validate_url("https://www.tiktok.com/@a/video/1", resolve=False)
    assert validate_url("https://instagram.com/reel/abc/", resolve=False)


def test_ratelimit():
    r = RateLimiter(limit=2, window=60)
    assert r.allow("a") and r.allow("a") and not r.allow("a") and r.allow("b")
