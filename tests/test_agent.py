"""Tests the Agent's control flow with a fully fake LLM client - no network,
no API key needed. Run with: pytest tests/test_agent.py -v
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import Agent, extract_json  # noqa: E402


class FakeMessages:
    def __init__(self, script):
        # script: list of fake responses to return on successive .create() calls
        self._script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._script.pop(0)


class FakeClient:
    def __init__(self, script):
        self.messages = FakeMessages(script)


def tool_use_block(name, tool_input, block_id="tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def test_extract_json_pulls_object_out_of_prose():
    text = 'sure, here it is: {"answer": {"state": "Assam"}, "log_url": "x"} thanks'
    assert json.loads(extract_json(text)) == {"answer": {"state": "Assam"}, "log_url": "x"}


def test_agent_runs_tool_then_returns_final_json():
    # Turn 1: model asks to run_python
    turn1 = SimpleNamespace(
        stop_reason="tool_use",
        content=[tool_use_block("run_python", {"code": "print(42)"})],
    )
    # Turn 2: model gives final answer after seeing tool result
    turn2 = SimpleNamespace(
        stop_reason="end_turn",
        content=[text_block('{"answer": {"value": 42}}')],
    )
    fake_client = FakeClient([turn1, turn2])

    seen_tool_calls = []

    def fake_executor(name, tool_input):
        seen_tool_calls.append((name, tool_input))
        return "42\n"

    agent = Agent(client=fake_client, tool_executor=fake_executor)
    result = agent.run([{"role": "user", "content": "what is 6*7?"}])

    assert json.loads(result) == {"answer": {"value": 42}}
    assert seen_tool_calls == [("run_python", {"code": "print(42)"})]
    assert len(fake_client.messages.calls) == 2  # exactly two round-trips


def test_agent_gives_up_after_max_turns():
    # Model that ALWAYS wants another tool call - agent must not loop forever
    infinite_turn = SimpleNamespace(
        stop_reason="tool_use",
        content=[tool_use_block("fetch_url", {"url": "http://x"})],
    )
    fake_client = FakeClient([infinite_turn] * 3)
    agent = Agent(
        client=fake_client,
        tool_executor=lambda n, i: "data",
        max_turns=3,
    )
    result = agent.run([{"role": "user", "content": "loop forever"}])
    assert json.loads(result) == {"error": "max_turns_exceeded"}
    assert len(fake_client.messages.calls) == 3


if __name__ == "__main__":
    test_extract_json_pulls_object_out_of_prose()
    test_agent_runs_tool_then_returns_final_json()
    test_agent_gives_up_after_max_turns()
    print("all agent tests passed")
