import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app.agent import Agent

LOG_PATH = os.environ.get("LOG_PATH", "run.jsonl")
LOG_URL = os.environ.get("LOG_URL", "https://your-host.example.com/run.jsonl")

app = FastAPI()
_history: dict[int, list] = {}
_agent = Agent()


def build_final_reply(raw_model_output: str, log_url: str = LOG_URL) -> str:
    """Take whatever JSON the model produced, force in the required log_url key,
    and return a clean single-line JSON string. Falls back to a minimal
    envelope if the model's output wasn't valid JSON."""
    try:
        obj = json.loads(raw_model_output)
        if not isinstance(obj, dict):
            obj = {"answer": obj}
    except (json.JSONDecodeError, TypeError):
        obj = {"answer": raw_model_output}
    obj["log_url"] = log_url
    return json.dumps(obj, ensure_ascii=False)


def log_run(chat_id: int, question: str, reply: str) -> None:
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps({"chat_id": chat_id, "question": question, "reply": reply}) + "\n")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/run.jsonl")
def get_log():
    if not os.path.exists(LOG_PATH):
        open(LOG_PATH, "a").close()
    return FileResponse(LOG_PATH, media_type="application/json")


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
