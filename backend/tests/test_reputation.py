import pytest
from fastapi.testclient import TestClient

from app.services.reputation_service import risk_level_for


def test_green_message_keeps_reputation_capped_at_100(send) -> None:
    result = send("good morning everyone!", target=None)
    assert result["label"] == "green"
    assert result["sender_reputation"]["score"] == 100


def test_green_message_increases_reputation(send) -> None:
    send("you are useless")
    result = send("sorry, that was rude of me")
    assert result["label"] == "green"
    assert result["sender_reputation"]["score"] == 96


def test_yellow_message_decreases_reputation_by_5(send) -> None:
    result = send("you are useless")
    assert result["label"] == "yellow"
    assert result["sender_reputation"] == {"user_id": "u_101", "name": "Rohan", "score": 95, "risk_level": "good"}


def test_severe_message_decreases_reputation_by_20(send) -> None:
    result = send("kill yourself")
    assert result["label"] == "severe"
    assert result["sender_reputation"]["score"] == 80


def test_reputation_is_clamped_at_zero(send) -> None:
    for _ in range(6):
        result = send("i hope you die")
    assert result["sender_reputation"]["score"] == 0
    assert result["sender_reputation"]["risk_level"] == "dangerous"


@pytest.mark.parametrize(
    ("score", "level"),
    [(100, "good"), (80, "good"), (79, "watch"), (60, "watch"), (59, "risky"), (30, "risky"), (29, "dangerous"), (0, "dangerous")],
)
def test_risk_levels(score: int, level: str) -> None:
    assert risk_level_for(score) == level


def test_user_is_remembered_by_id_and_name(client: TestClient, send) -> None:
    send("hello", sender=("u_101", "Rohan"), target=("u_202", "Aman"))
    send("hello again", sender=("u_101", "Rohan"), target=("u_202", "Aman"))

    sender = client.get("/api/v1/users/u_101").json()
    target = client.get("/api/v1/users/u_202").json()
    assert (sender["name"], sender["total_messages"]) == ("Rohan", 2)
    assert (target["name"], target["total_messages"]) == ("Aman", 0)

    send("new display name", sender=("u_101", "Rohan K"))
    assert client.get("/api/v1/users/u_101").json()["name"] == "Rohan K"
    assert len(client.get("/api/v1/users").json()) == 2


def test_get_user_returns_reputation_data(client: TestClient, send) -> None:
    send("hi there")
    send("you are stupid")
    send("kys")

    response = client.get("/api/v1/users/u_101")
    assert response.status_code == 200
    assert response.json() == {
        "id": "u_101",
        "name": "Rohan",
        "reputation_score": 75,
        "risk_level": "watch",
        "total_messages": 3,
        "green_count": 1,
        "yellow_count": 1,
        "severe_count": 1,
    }


def test_get_unknown_user_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/users/nobody").status_code == 404


def test_list_users_filters_by_risk_level(client: TestClient, send) -> None:
    send("kill yourself", sender=("u_bad", "Bad"))
    send("kill yourself", sender=("u_bad", "Bad"))  # 60 -> watch
    send("hello", sender=("u_ok", "Ok"))

    watch = client.get("/api/v1/users", params={"risk_level": "watch"}).json()
    assert [u["id"] for u in watch] == ["u_bad"]
    assert client.get("/api/v1/users", params={"risk_level": "nope"}).status_code == 422


def test_user_messages_history(client: TestClient, send) -> None:
    send("you are useless")
    send("hello")
    messages = client.get("/api/v1/users/u_101/messages").json()
    assert {m["label"] for m in messages} == {"yellow", "green"}
    assert len(client.get("/api/v1/users/u_202/messages").json()) == 2
