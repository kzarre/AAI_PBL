from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_is_served(client: TestClient) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_list_messages_filters_by_label(client: TestClient, send) -> None:
    send("hello")
    send("kill yourself")
    severe = client.get("/api/v1/messages", params={"label": "severe"}).json()
    assert [m["text"] for m in severe] == ["kill yourself"]
    assert len(client.get("/api/v1/messages").json()) == 2
