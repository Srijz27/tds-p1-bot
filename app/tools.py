"""Client-side tool implementations the agent can call.

These run in your server process, so keep run_python sandboxed enough for
your comfort level (this is a minimal exec-based sandbox - fine for a
grading exercise, NOT fine for untrusted production traffic).
"""
import contextlib
import io

import requests


def fetch_url(url: str, timeout: int = 30, max_chars: int = 20000) -> str:
    """Fetch raw text/CSV/HTML content of a URL."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "tds-p1-bot/1.0"})
        r.raise_for_status()
        return r.text[:max_chars]
    except Exception as e:  # noqa: BLE001
        return f"ERROR fetching {url}: {e}"


def run_python(code: str, max_chars: int = 8000) -> str:
    """Execute Python code (pandas/numpy available) and return captured stdout."""
    import numpy as np
    import pandas as pd

    buf = io.StringIO()
    safe_globals = {"pd": pd, "np": np, "__builtins__": __builtins__}
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, safe_globals)  # noqa: S102
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"
    out = buf.getvalue()
    return out[:max_chars] if out else "(no stdout - use print() to return values)"


def default_tool_executor(name: str, tool_input: dict) -> str:
    if name == "fetch_url":
        return fetch_url(**tool_input)
    if name == "run_python":
        return run_python(**tool_input)
    return f"ERROR: unknown tool '{name}'"
