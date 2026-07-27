"""Exercises the webhook end-to-end (HTTP in, HTTP out) with the LLM agent
and Telegram send_message mocked - no API key, no bot token, no network.
Run with: pytest tests/test_main.py -v
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("LOG_PATH", "test_run.jsonl")
os.environ.setdefault("LOG_URL", "https://example.com/run.jsonl")

from fastapi.testclient import TestClient  # noqa: E402

from app import main as main_module  # noqa: E402

client = TestClient(main_module.app)


class FakeAgent:
    """Stands in for app.agent.Agent - returns a fixed 'model output' so we
    can check the webhook wires everything together correctly."""

    def run(self, messages):
        return '{"answer": {"state": "Assam"}}'


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_webhook_end_to_end(monkeypatch):
    # swap in the fake agent
    monkeypatch.setattr(main_module, "_agent", FakeAgent())
    # swap out the real Telegram send call
    sent = {}

    def fake_send_message(chat_id, text):
        sent["chat_id"] = chat_id
        sent["text"] = text

    monkeypatch.setattr("app.telegram.send_message", fake_send_message)

    # clean slate for the log file
    if os.path.exists(main_module.LOG_PATH):
        os.remove(main_module.LOG_PATH)

    payload = {
        "message": {
            "chat": {"id": 12345},
            "text": (
                'Which state has the highest maternal mortality rate? '
                'Reply with ONLY {"answer": {"state": "<name>"}, "log_url": "<url>"}'
            ),
        }
    }
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    # bot actually "sent" a message back
    assert sent["chat_id"] == 12345
    reply = json.loads(sent["text"])
    assert reply["answer"] == {"state": "Assam"}
    assert reply["log_url"] == "https://example.com/run.jsonl"

    # log file got a line written
    with open(main_module.LOG_PATH) as f:
        lines = f.readlines()
    assert len(lines) == 1
    logged = json.loads(lines[0])
    assert logged["chat_id"] == 12345


def test_run_jsonl_is_servable():
    r = client.get("/run.jsonl")
    assert r.status_code == 200


if __name__ == "__main__":
    test_health()
    print("health check passed")
