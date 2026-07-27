"""LLM agent core.

The Anthropic client and tool executor are constructor args so this class
can be fully unit-tested with fakes (see tests/test_agent.py) without any
real API key or network access.
"""
import json
import os
import re

from app.tools import default_tool_executor

SYSTEM_PROMPT = """You are a rigorous data analyst agent answering questions \
sent over Telegram, typically referencing MOSPI or other Indian public \
datasets.

Rules:
- Use the web_search and fetch_url tools to find real public data. Never \
  guess numbers from memory.
- Use run_python (pandas/numpy available) to actually compute answers from \
  real data you fetched - do not eyeball numbers from search snippets.
- Your FINAL reply must be ONLY the exact JSON object the user's message \
  specifies (same keys / same shape as requested). No markdown, no code \
  fences, no explanation before or after it.
"""

TOOLS = [
    {"type": "web_search_20250305", "name": "web_search"},
    {
        "name": "fetch_url",
        "description": "Fetch raw text/CSV/HTML content of a public URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute Python code (pandas as pd, numpy as np available) and "
            "return whatever is print()'ed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
]


def extract_json(text: str) -> str:
    """Pull the first {...} block out of a text response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text.strip()


class Agent:
    def __init__(self, client=None, tool_executor=None, model="claude-sonnet-4-5", max_turns=8):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.client = client
        self.tool_executor = tool_executor or default_tool_executor
        self.model = model
        self.max_turns = max_turns

    def run(self, messages: list) -> str:
        """messages: list of {"role": "user"/"assistant", "content": ...}
        Returns a JSON string (best-effort extracted from the model's reply).
        """
        convo = list(messages)
        for _ in range(self.max_turns):
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=convo,
            )

            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if b.type == "text")
                return extract_json(text)

            convo.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = self.tool_executor(block.name, block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            convo.append({"role": "user", "content": tool_results})

        return json.dumps({"error": "max_turns_exceeded"})
