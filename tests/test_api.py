from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_index():
    r = c.get("/")
    assert r.status_code == 200 and "nosniff" in r.headers["x-content-type-options"]


def test_bad_url():
    r = c.post("/api/download", json={"url": "http://127.0.0.1/"})
    assert r.status_code == 400
