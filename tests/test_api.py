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
