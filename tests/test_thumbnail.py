import io

import app.main as m
import app.thumbnail as t
from fastapi.testclient import TestClient

c = TestClient(m.app)


class FakeResp(io.BytesIO):
    def __init__(self, data, ctype="image/jpeg", status=200):
        super().__init__(data)
        self.status = status
        self.headers = type("H", (), {"get_content_type": lambda _: ctype})()


def fake_open(resp):
    return type("O", (), {"open": lambda _, url, timeout: resp})()


def test_rejects_private_and_bad_scheme():
    assert t.fetch_thumbnail("http://127.0.0.1/a.jpg") is None
    assert t.fetch_thumbnail("file:///etc/passwd") is None
    assert t.fetch_thumbnail(None) is None


def test_data_uri(monkeypatch):
    monkeypatch.setattr(t, "_public_host", lambda u: True)
    monkeypatch.setattr(t, "_opener", fake_open(FakeResp(b"\xff\xd8abc")))
    assert t.fetch_thumbnail("https://i.ytimg.com/a.jpg") == "data:image/jpeg;base64,/9hhYmM="


def test_rejects_large_or_wrong_type(monkeypatch):
    monkeypatch.setattr(t, "_public_host", lambda u: True)
    monkeypatch.setattr(t, "_opener", fake_open(FakeResp(b"x" * (t.MAX_BYTES + 1))))
    assert t.fetch_thumbnail("https://i.ytimg.com/a.jpg") is None
    monkeypatch.setattr(t, "_opener", fake_open(FakeResp(b"<svg/>", "image/svg+xml")))
    assert t.fetch_thumbnail("https://i.ytimg.com/a.svg") is None


class FakeYDL:
    def __init__(self, opts): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def extract_info(self, url, download):
        return {"title": "T", "uploader": "U", "duration": 19, "extractor_key": "Youtube", "thumbnail": "https://x/a.jpg"}


def test_info_includes_thumbnail(monkeypatch):
    monkeypatch.setattr(m, "validate_url", lambda u: u)
    monkeypatch.setattr(m.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(m, "fetch_thumbnail", lambda u: "data:image/jpeg;base64,AA==")
    r = c.post("/api/info", json={"url": "https://youtube.com/watch?v=1"})
    assert r.status_code == 200 and r.json()["thumbnail"] == "data:image/jpeg;base64,AA=="
    monkeypatch.setattr(m, "fetch_thumbnail", lambda u: None)
    r = c.post("/api/info", json={"url": "https://youtube.com/watch?v=1"})
    assert r.status_code == 200 and r.json()["thumbnail"] is None and r.json()["title"] == "T"
