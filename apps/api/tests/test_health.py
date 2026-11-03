def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "cloudfinops-ai"


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready(client):
    r = client.get("/api/v1/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"