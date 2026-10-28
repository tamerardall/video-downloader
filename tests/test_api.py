from pathlib import Path

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
        assert r.status_code == 422 and "COOKIES_FROM_BROWSER" in r.json()["detail"]


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
    assert "Invalid request body" in caplog.text


def test_json_errors_named_error_json():
    # The iOS Shortcut recognises error responses by their file extension (json)
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"})
    assert 'filename="error.json"' in r.headers["content-disposition"]


def test_download_prefers_iphone_codecs_and_logs(monkeypatch, caplog):
    # iPhone Photos won't save VP9/AV1; H.264 + AAC must be preferred
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
    assert seen["format_sort"][0] == "vcodec:h264" and "acodec:aac" in seen["format_sort"]
    assert "avc1.64001F" in caplog.text and "abc.mp4" in caplog.text


def test_format_sort_picks_hd_h264_over_muxed_360p():
    # YouTube: the old muxed 360p file (with audio) must not beat 1080p H.264 video+audio,
    # and VP9/AV1 must not win despite a higher bitrate (iPhone can't save them)
    import yt_dlp
    import app.main as m

    def f(i, vc, ac, h=None, ext="mp4", tbr=1000):
        return {"format_id": i, "url": f"http://x/{i}", "ext": ext, "vcodec": vc,
                "acodec": ac, "height": h, "tbr": tbr}

    fmts = [
        f("18", "avc1.42001E", "mp4a.40.2", 360, tbr=444),
        f("137", "avc1.640028", "none", 1080, tbr=3038),
        f("399", "av01.0.08M.08", "none", 1080, tbr=1142),
        f("248", "vp9", "none", 1080, ext="webm", tbr=4000),
        f("140", "none", "mp4a.40.2", ext="m4a", tbr=129),
        f("251", "none", "opus", ext="webm", tbr=160),
    ]
    opts = {"quiet": True, "simulate": True, "format": m.FORMAT,
            "format_sort": m.FORMAT_SORT, "merge_output_format": "mp4"}
    with yt_dlp.YoutubeDL(opts) as y:
        r = y.process_ie_result({"id": "t", "title": "t", "formats": fmts, "extractor": "x",
                                 "extractor_key": "x", "webpage_url": "http://x"},
                                download=False)
    assert r["format_id"] == "137+140"


def test_deno_from_venv(monkeypatch):
    # JS runtime for YouTube; the server may run without the venv activated
    import app.main as m
    monkeypatch.setattr(m, "DENO", "/venv/bin/deno")
    assert m._opts()["js_runtimes"] == {"deno": {"path": "/venv/bin/deno"}}
    monkeypatch.setattr(m, "DENO", None)
    assert "js_runtimes" not in m._opts()


def test_cookies_from_browser_windows_path(monkeypatch):
    # Only the first colon separates browser and profile; drive letters stay intact
    import app.main as m
    monkeypatch.setattr(m, "COOKIES_FROM_BROWSER", "firefox:C:\\Users\\me\\profile")
    assert m._opts()["cookiesfrombrowser"] == ("firefox", "C:\\Users\\me\\profile")


def test_ffmpeg_location():
    # A system ffmpeg or the imageio-ffmpeg binary; either way yt-dlp gets a real file
    import app.main as m
    assert Path(m._opts()["ffmpeg_location"]).is_file()


def test_dotenv_loaded(tmp_path):
    # app/__init__.py loads the project's .env unless VD_NO_DOTENV is set
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    env = {k: v for k, v in os.environ.items() if k not in ("VD_NO_DOTENV", "PORT")}
    code = ("import dotenv, os; dotenv.load_dotenv = lambda p, override: "
            "os.environ.setdefault('PORT', str(p)); import app; print(os.environ['PORT'])")
    out = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == str(root / ".env")
