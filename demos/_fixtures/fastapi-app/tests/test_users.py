from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user_returns_201():
    res = client.post("/users", json={"email": "a@example.com", "display_name": "A"})
    assert res.status_code == 201
    assert res.json()["email"] == "a@example.com"


def test_get_missing_user_returns_404():
    res = client.get("/users/999")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
