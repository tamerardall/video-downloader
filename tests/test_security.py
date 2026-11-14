import pytest

from app import security
from app.security import InvalidURL, RateLimiter, _parse_domains, check_media_url, validate_url


@pytest.fixture
def only_tiktok(monkeypatch):
    monkeypatch.setattr(security, "ALLOWED_DOMAINS", ("tiktok.com",))


@pytest.fixture
def unrestricted(monkeypatch):
    monkeypatch.setattr(security, "ALLOWED_DOMAINS", ())


@pytest.mark.parametrize("u", [
    "file:///etc/passwd", "ftp://tiktok.com/x", "https://user:pw@tiktok.com/",
    "", "x" * 3000,
])
def test_rejects(u, unrestricted):
    with pytest.raises(InvalidURL):
        validate_url(u, resolve=False)


@pytest.mark.parametrize("u", [
    "http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/", "http://[::1]/",
])
def test_rejects_private_hosts_without_allowlist(u, unrestricted):
    with pytest.raises(InvalidURL):
        validate_url(u)


@pytest.mark.parametrize("u", ["https://evil.com/", "https://tiktok.com.evil.com/"])
def test_allowlist_rejects(u, only_tiktok):
    with pytest.raises(InvalidURL):
        validate_url(u, resolve=False)


def test_accepts(only_tiktok):
    assert validate_url("https://www.tiktok.com/@a/video/1", resolve=False)


def test_no_allowlist_accepts_any_public_host(unrestricted):
    assert validate_url("https://example.org/v.mp4", resolve=False)


@pytest.mark.parametrize("raw", ["", " ", ",", None])
def test_empty_env_means_unrestricted(raw):
    assert _parse_domains(raw) == ()


def test_parse_domains_lowercases_and_strips():
    assert _parse_domains(" TikTok.com, x.com ,") == ("tiktok.com", "x.com")


@pytest.mark.parametrize("u", [
    "file:///etc/passwd", "rtmp://example.org/x", "https://u:p@example.org/x", "",
])
def test_check_media_url_rejects(u):
    with pytest.raises(InvalidURL):
        check_media_url(u, resolve=False)


@pytest.mark.parametrize("u", [
    "http://[::1]/", "http://localhost/x.mp4", "http://127.0.0.1/x.mp4",
])
def test_check_media_url_rejects_loopback(u):
    with pytest.raises(InvalidURL):
        check_media_url(u)


def test_check_media_url_ignores_allowlist(only_tiktok):
    assert check_media_url("https://cdn.example.org/v.mp4", resolve=False)


def test_check_media_url_rejects_private_resolution(monkeypatch):
    def fake(ip):
        return lambda *a, **k: [(2, 1, 6, "", (ip, 0))]
    monkeypatch.setattr(security.socket, "getaddrinfo", fake("10.0.0.5"))
    with pytest.raises(InvalidURL):
        check_media_url("https://cdn.example.org/v.mp4")
    monkeypatch.setattr(security.socket, "getaddrinfo", fake("93.184.216.34"))
    assert check_media_url("https://cdn.example.org/v.mp4")


def test_ratelimit():
    r = RateLimiter(limit=2, window=60)
    assert r.allow("a") and r.allow("a") and not r.allow("a") and r.allow("b")
