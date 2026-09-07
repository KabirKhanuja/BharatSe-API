"""The app boots and the contract is stable, without a database present."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_responds():
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_health_reports_a_missing_database_rather_than_crashing():
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "database" in body


def test_openapi_lists_the_routes_the_app_depends_on():
    paths = client.get("/api/v1/openapi.json").json()["paths"]

    for expected in (
        "/api/v1/auth/otp/verify",
        "/api/v1/products/sync",
        "/api/v1/listings/generate",
        "/api/v1/pricing/suggest",
        "/api/v1/passports/verify",
    ):
        assert expected in paths, f"missing route {expected}"


def test_protected_routes_reject_an_anonymous_caller():
    assert client.get("/api/v1/products").status_code == 401
