from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_index():
    r = c.get("/")
    assert r.status_code == 200 and "nosniff" in r.headers["x-content-type-options"]


def test_bad_url():
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"})
    assert r.status_code == 400


def test_token_required(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "API_TOKEN", "s3cret")
    body = {"url": "https://www.tiktok.com/@a/video/1"}
    assert c.post("/api/download", json=body).status_code == 401
    assert c.post("/api/download", json=body, headers={"Authorization": "Bearer x"}).status_code == 401
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"}, headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 400


def test_cookie_opts(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "COOKIES_FILE", "/x/cookies.txt")
    monkeypatch.setattr(m, "COOKIES_FROM_BROWSER", "firefox")
    o = m._opts()
    assert o["cookiefile"] == "/x/cookies.txt"
    assert o["cookiesfrombrowser"] == ("firefox", None)
    monkeypatch.setattr(m, "COOKIES_FROM_BROWSER", "brave:/p/Default")
    assert m._opts()["cookiesfrombrowser"] == ("brave", "/p/Default")
    monkeypatch.setattr(m, "COOKIES_FILE", "")
    monkeypatch.setattr(m, "COOKIES_FROM_BROWSER", "")
    o = m._opts()
    assert "cookiefile" not in o and "cookiesfrombrowser" not in o


def test_login_required_message(monkeypatch):
    import app.main as m
    import yt_dlp

    class Fake:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def extract_info(self, *a, **k):
            raise yt_dlp.utils.DownloadError(
                "ERROR: [Instagram] x: Instagram sent an empty media response. "
                "use --cookies-from-browser or --cookies for the authentication.")

    monkeypatch.setattr(m.yt_dlp, "YoutubeDL", Fake)
    monkeypatch.setattr(m, "validate_url", lambda u: u)
    body = {"url": "https://www.instagram.com/reel/x/"}
    for path in ("/api/info", "/api/download"):
        r = c.post(path, json=body)
        assert r.status_code == 422 and "çerez" in r.json()["detail"]
