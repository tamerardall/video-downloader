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


def test_ytdlp_error_shown_and_logged(monkeypatch, caplog):
    import app.main as m
    import yt_dlp

    class Fake:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def extract_info(self, *a, **k):
            raise yt_dlp.utils.DownloadError(
                "\x1b[0;31mERROR:\x1b[0m [Instagram] abc: HTTP Error 400: Bad Request")

    monkeypatch.setattr(m.yt_dlp, "YoutubeDL", Fake)
    monkeypatch.setattr(m, "validate_url", lambda u: u)
    body = {"url": "https://www.instagram.com/reel/abc/"}
    for path in ("/api/info", "/api/download"):
        caplog.clear()
        r = c.post(path, json=body)
        detail = r.json()["detail"]
        assert r.status_code == 422
        assert "[Instagram] abc: HTTP Error 400: Bad Request" in detail
        assert "\x1b" not in detail and "ERROR:" not in detail
        assert "HTTP Error 400" in caplog.text


def test_url_extracted_from_shared_text(monkeypatch):
    import app.main as m
    seen = []
    monkeypatch.setattr(m, "validate_url", lambda u: seen.append(u) or u)

    class Fake:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def extract_info(self, *a, **k): raise RuntimeError("x")

    monkeypatch.setattr(m.yt_dlp, "YoutubeDL", Fake)
    text = "Bu reel'e bak\nhttps://www.instagram.com/reel/abc/?igsh=xyz "
    c.post("/api/info", json={"url": text})
    assert seen == ["https://www.instagram.com/reel/abc/?igsh=xyz"]


def test_rejection_logged(caplog):
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"})
    assert r.status_code == 400 and "127.0.0.1" in caplog.text


def test_bad_body_logged(caplog):
    r = c.post("/api/download", content="url=x")
    assert r.status_code == 422 and "url" in r.json()["detail"]
    assert "Geçersiz istek gövdesi" in caplog.text


def test_json_errors_named_hata_json():
    # Kısayol hata yanıtını dosya uzantısından (json) tanıyor
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"})
    assert 'filename="hata.json"' in r.headers["content-disposition"]


def test_download_prefers_iphone_codecs_and_logs(monkeypatch, caplog):
    # iPhone Fotoğraflar VP9/AV1 kaydetmiyor; H.264 + AAC öncelikli olmalı
    import app.main as m
    from pathlib import Path
    seen = {}

    class Fake:
        def __init__(self, opts): seen.update(opts)
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def extract_info(self, *a, **k):
            out = Path(seen["outtmpl"]).parent / "abc.mp4"
            out.write_bytes(b"x" * 10)
            return {"vcodec": "avc1.64001F", "acodec": "mp4a.40.2"}

    monkeypatch.setattr(m.yt_dlp, "YoutubeDL", Fake)
    monkeypatch.setattr(m, "validate_url", lambda u: u)
    caplog.set_level("INFO", logger="uvicorn.error")
    r = c.post("/api/download", json={"url": "https://www.instagram.com/reel/abc/"})
    assert r.status_code == 200
    assert seen["format_sort"][:2] == ["vcodec:h264", "acodec:aac"]
    assert "avc1.64001F" in caplog.text and "abc.mp4" in caplog.text
