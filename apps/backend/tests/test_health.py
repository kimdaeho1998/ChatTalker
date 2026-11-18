from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_available_without_database() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "chatalker-backend",
        "database": "not_checked",
    }
