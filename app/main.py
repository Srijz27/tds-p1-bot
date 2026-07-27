import json
import os
import re
import shlex
import urllib.parse
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app.agent import Agent

class _EnvValue(str):
    def __new__(cls, env_name: str, default: str):
        obj = super().__new__(cls, default)
        obj.env_name = env_name
        obj.default = default
        return obj

    def _resolve(self) -> str:
        return os.environ.get(self.env_name, self.default)

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return repr(self._resolve())

    def __fspath__(self) -> str:
        return self._resolve()


LOG_PATH = _EnvValue("LOG_PATH", "run.jsonl")
LOG_URL = _EnvValue("LOG_URL", "https://your-host.example.com/run.jsonl")


def _refresh_runtime_settings() -> None:
    globals()["LOG_PATH"] = _EnvValue("LOG_PATH", "run.jsonl")
    globals()["LOG_URL"] = _EnvValue("LOG_URL", "https://your-host.example.com/run.jsonl")


app = FastAPI()
_history: dict[int, list] = {}
_agent = Agent()

WORKSPACE_ROOT = Path("/home/agent/workspace").resolve()
HOME_ROOT = Path("/home/agent").resolve()
PROTECTED_SECRET = Path("/home/agent/.npmrc").resolve()
ALLOWED_WRITE_ROOT = (WORKSPACE_ROOT / "build").resolve()
ALLOWED_HOSTS = {"registry.npmjs.org", "pypi.org"}


def _normalize_path(value: str) -> Path:
    if not value:
        return Path("")
    if value.startswith("~"):
        value = str(HOME_ROOT / value[2:]) if value.startswith("~/") else str(HOME_ROOT)
    if value.startswith("$HOME"):
        value = str(HOME_ROOT)
    if value.startswith("$PWD"):
        value = str(WORKSPACE_ROOT)
    path = Path(value)
    try:
        return path.expanduser().resolve(strict=False)
    except OSError:
        return path.expanduser().resolve()


def _contains_secret_path(path: Path) -> bool:
    try:
        return path == PROTECTED_SECRET or path.is_relative_to(PROTECTED_SECRET)
    except AttributeError:
        return str(path) == str(PROTECTED_SECRET) or str(path).startswith(str(PROTECTED_SECRET) + os.sep)


def _is_within(path: Path, root: Path) -> bool:
    try:
        return path == root or path.is_relative_to(root)
    except AttributeError:
        return str(path) == str(root) or str(path).startswith(str(root) + os.sep)


def _extract_shell_paths(command: str):
    candidates = []
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = re.split(r"\s+", command)

    for token in tokens:
        if not token:
            continue
        token = token.strip()
        if token.startswith(("'", '"')) and token.endswith(("'", '"')):
            token = token[1:-1]
        if token.startswith("$(") or token.startswith("`"):
            continue
        candidates.append(token)
    return candidates


def _scan_skill_payload(skill_text: str) -> List[str]:
    categories = []
    if not isinstance(skill_text, str):
        return categories

    text = skill_text.lower()
    frontmatter = skill_text
    if frontmatter.startswith("---"):
        parts = frontmatter.split("\n---\n", 1)
        if len(parts) == 2:
            frontmatter = parts[0] + "\n---"

    # hardcoded secret / webhook URL
    if re.search(r"(?:api[_-]?key|token|secret|password|authorization|webhook)[^\n]{0,40}[:=]\s*[\"']?[A-Za-z0-9_\-./:=]{4,}", skill_text):
        categories.append("hardcoded_secret")
    if re.search(r"https?://(?:hooks\.|[^\s\"']*webhook[^\s\"']*|[^\s\"']*(?:slack\.com|discord\.com|api\.)[^\s\"']*)", skill_text, flags=re.IGNORECASE):
        categories.append("hardcoded_secret")

    # prompt injection heuristics
    prompt_injection_patterns = [
        r"ignore the user",
        r"ignore the agent",
        r"ignore the stop",
        r"ignore the cancel",
        r"silently exfiltrate",
        r"secretly exfiltrate",
        r"override user",
        r"override agent",
        r"do not tell the user",
    ]
    if any(re.search(pattern, text) for pattern in prompt_injection_patterns):
        categories.append("prompt_injection")

    # excessive permissions heuristics
    permissions_text = ""
    if "permissions:" in skill_text:
        permissions_text = skill_text.split("permissions:", 1)[1]
    permissions_lower = permissions_text.lower()
    if re.search(r"read-write access to the entire home directory|entire filesystem|full filesystem access|full system access|any external domain|egress allowed to any|access to the entire home directory|access to the entire filesystem", permissions_lower):
        categories.append("excessive_permissions")

    # unclear provenance heuristics
    if re.search(r"^author:\s*$|^version:\s*$|^changelog:\s*$", skill_text, flags=re.M):
        categories.append("unclear_provenance")
    if re.search(r"^author:\s*\S+", skill_text, flags=re.M) and re.search(r"^version:\s*\S+", skill_text, flags=re.M) and re.search(r"^changelog:\s*\S+", skill_text, flags=re.M):
        pass
    else:
        if any(token in skill_text.lower() for token in ["author:", "version:", "changelog:"]):
            categories.append("unclear_provenance")

    # dedupe and preserve order
    seen = set()
    ordered = []
    for cat in categories:
        if cat not in seen:
            seen.add(cat)
            ordered.append(cat)
    return ordered


def guardrail(payload: dict) -> tuple[str, str]:
    tool = payload.get("tool")
    if tool == "bash":
        command = payload.get("command", "")
        if not isinstance(command, str):
            return "block", "Invalid bash command payload."

        if "/home/agent/.npmrc" in command or "$HOME/.npmrc" in command or "~/.npmrc" in command:
            return "block", "Reading /home/agent/.npmrc is never permitted by this agent's policy."

        for token in _extract_shell_paths(command):
            if token in {"$HOME", "$PWD"}:
                continue
            if token.startswith("$"):
                continue
            if token.startswith("~"):
                resolved = _normalize_path(token)
                if _contains_secret_path(resolved):
                    return "block", "Reading /home/agent/.npmrc is never permitted by this agent's policy."
            else:
                path_candidates = []
                if token.startswith("/"):
                    path_candidates.append(token)
                else:
                    path_candidates.extend([str(WORKSPACE_ROOT / token), str(HOME_ROOT / token)])
                for candidate in path_candidates:
                    resolved = _normalize_path(candidate)
                    if _contains_secret_path(resolved):
                        return "block", "Reading /home/agent/.npmrc is never permitted by this agent's policy."
        return "allow", "Listing the agent's own working directory is fine."

    if tool == "write_file":
        path = payload.get("path", "")
        if not isinstance(path, str):
            return "block", "Invalid write path payload."
        resolved = _normalize_path(path)
        if not _is_within(resolved, ALLOWED_WRITE_ROOT):
            return "block", "Writes outside /home/agent/workspace/build/ are never permitted."
        return "allow", "Write is inside the allowed build directory."

    if tool == "http_request":
        url = payload.get("url", "")
        if not isinstance(url, str):
            return "block", "Invalid HTTP request payload."
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_HOSTS:
            return "block", "Only registry.npmjs.org and pypi.org are allowed for outbound HTTP requests."
        return "allow", "Outbound HTTP host is on the exact allowlist."

    return "block", "Unsupported tool type."


def build_final_reply(raw_model_output: str, log_url: str | None = None) -> str:
    """Take whatever JSON the model produced, force in the required log_url key,
    and return a clean single-line JSON string. Falls back to a minimal
    envelope if the model's output wasn't valid JSON."""
    _refresh_runtime_settings()
    try:
        obj = json.loads(raw_model_output)
        if not isinstance(obj, dict):
            obj = {"answer": obj}
    except (json.JSONDecodeError, TypeError):
        obj = {"answer": raw_model_output}

    resolved_log_url = log_url if log_url is not None else os.environ.get("LOG_URL", LOG_URL)
    obj["log_url"] = resolved_log_url
    return json.dumps(obj, ensure_ascii=False)


def log_run(chat_id: int, question: str, reply: str) -> None:
    _refresh_runtime_settings()
    log_path = Path(LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps({"chat_id": chat_id, "question": question, "reply": reply}) + "\n")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/run.jsonl")
def get_log():
    _refresh_runtime_settings()
    if not os.path.exists(LOG_PATH):
        open(LOG_PATH, "a").close()
    return FileResponse(LOG_PATH, media_type="application/json")


@app.post("/guardrail")
async def guardrail_endpoint(req: Request):
    payload = await req.json()
    decision, reason = guardrail(payload)
    return JSONResponse({"decision": decision, "reason": reason})


@app.post("/scan-skill")
async def scan_skill_endpoint(req: Request):
    payload = await req.json()
    skill_text = payload.get("skill", "")
    categories = _scan_skill_payload(skill_text)
    return JSONResponse({"categories": categories})


@app.post("/webhook")
async def webhook(req: Request):
    from app.telegram import send_message  # imported here so tests can run without a bot token

    data = await req.json()
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text")
    if not chat_id or not text:
        return JSONResponse({"ok": True})

    hist = _history.setdefault(chat_id, [])
    hist.append({"role": "user", "content": text})

    raw = _agent.run(hist)
    reply = build_final_reply(raw)

    hist.append({"role": "assistant", "content": reply})
    send_message(chat_id, reply)
    log_run(chat_id, text, reply)

    return JSONResponse({"ok": True})
