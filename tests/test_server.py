from fastapi.testclient import TestClient
from mathtran.server import app

c = TestClient(app)

def test_index_and_health():
    assert c.get("/").status_code == 200
    h = c.get("/api/health").json()
    assert "tectonic" in h and h["model"]

def test_export_svg():
    r = c.post("/api/export/svg", json={"latex": "x^2+y^2=z^2"})
    assert r.status_code == 200 and b"<svg" in r.content

def test_export_bad_latex():
    assert c.post("/api/export/pdf", json={"latex": "\\bad{"}).status_code == 400


def test_icon():
    r = c.get('/icon.svg')
    assert r.status_code == 200 and b'<svg' in r.content
