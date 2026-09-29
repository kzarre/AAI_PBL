import pytest
from fastapi.testclient import TestClient

from app.agent import moderation_agent
from app.schemas.moderation_schema import AgentOutput, AIResult, RecentContext, RuleResult
from app.tools import decision_engine, rule_checker


@pytest.mark.parametrize("text", ["kill yourself", "Just KILL YOURSELF already", "kys loser", "I will kill you"])
def test_severe_patterns_are_always_severe(send, text: str) -> None:
    assert send(text)["label"] == "severe"


def test_kill_yourself_overrides_green_llm_result() -> None:
    output = AgentOutput(
        ai=AIResult(label="green", confidence=0.99, reason="Looks fine.", recommended_action="None."),
        rules=rule_checker.check("kill yourself"),
        source="llm",
    )
    decision = decision_engine.decide(output, RecentContext(), sender_reputation=100)
    assert decision.label == "severe"
    assert decision.escalated


def test_basic_labels(send) -> None:
    assert send("hey, want to study together later?")["label"] == "green"
    assert send("you are useless")["label"] == "yellow"


def test_three_yellow_messages_to_same_target_escalate(send) -> None:
    assert send("you are useless")["label"] == "yellow"
    assert send("you are so dumb")["label"] == "yellow"
    third = send("what an idiot")
    assert third["label"] == "severe"
    assert "Repeated targeted abuse" in third["reason"]


def test_yellow_messages_to_different_targets_do_not_escalate(send) -> None:
    for i in range(3):
        assert send("you are useless", target=(f"u_{i}", f"Target{i}"))["label"] == "yellow"


def test_low_reputation_escalates_yellow() -> None:
    output = AgentOutput(
        ai=AIResult(label="yellow", confidence=0.8, reason="Insult.", recommended_action="Warn."),
        rules=RuleResult(label="yellow", matches=["stupid"]),
        source="rules",
    )
    assert decision_engine.decide(output, RecentContext(), sender_reputation=25).label == "severe"
    assert decision_engine.decide(output, RecentContext(), sender_reputation=30).label == "yellow"


def test_invalid_llm_output_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenClient:
        def complete_json(self, *_: str) -> dict:
            return {"label": "purple", "confidence": 5}

    monkeypatch.setattr(moderation_agent, "get_llm_client", lambda: BrokenClient())
    output = moderation_agent.classify("you are stupid", "Rohan", "Aman", RecentContext())
    assert output.source == "rules"
    assert output.ai.label == "yellow"


def test_duplicate_message_id_is_rejected(client: TestClient, send) -> None:
    send("hello")  # msg_001
    payload = {"message_id": "msg_001", "sender": {"id": "u_101", "name": "Rohan"}, "text": "hi again"}
    assert client.post("/api/v1/messages/classify", json=payload).status_code == 409


def test_invalid_payload_is_rejected(client: TestClient) -> None:
    payload = {"message_id": "m1", "sender": {"id": "u_1", "name": "A"}, "text": ""}
    assert client.post("/api/v1/messages/classify", json=payload).status_code == 422
