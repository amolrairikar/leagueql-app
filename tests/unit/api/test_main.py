from fastapi.testclient import TestClient

from api.main import APIResponse, app

client = TestClient(app)


class TestRoot:
    def test_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_healthy_detail(self):
        response = client.get("/")
        assert response.json() == {"detail": "Healthy!", "data": None}


class TestAPIResponse:
    def test_detail_only(self):
        model = APIResponse(detail="ok")
        assert model.detail == "ok"
        assert model.data is None

    def test_detail_with_data(self):
        model = APIResponse(detail="ok", data={"key": "value"})
        assert model.data == {"key": "value"}
