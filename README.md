# TDS P1 — Data Analyst Telegram Bot

An LLM agent (Claude + web_search + a Python sandbox tool) that answers
data-analysis questions sent over Telegram and replies with exactly one
JSON object: `{"answer": ..., "log_url": "..."}`.

## How it works

```
Telegram message → POST /webhook → Agent (Claude + tools loop) → JSON reply
                                                                → logged to run.jsonl
```

- `app/agent.py` — the LLM tool-use loop (web_search, fetch_url, run_python)
- `app/tools.py` — real implementations of fetch_url / run_python
- `app/telegram.py` — sendMessage / setWebhook helpers
- `app/main.py` — FastAPI app: webhook route, `/run.jsonl` log route, `/health`
- `tests/` — unit + integration tests with the LLM and Telegram calls faked
  out (no API key/network needed to run these)

## Local setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your real tokens
```

Run the tests (no keys required — everything's mocked):
```bash
pytest tests/ -v
```

Run the server locally:
```bash
export $(cat .env | xargs)
uvicorn app.main:app --reload
```

To actually test against Telegram locally, tunnel it (e.g. `ngrok http 8000`)
and point the webhook at the tunnel URL (see Deploy step 3 below).

## Deploy (Railway / Render / Fly — pick one)

1. Push this repo to GitHub (public).
2. Create a new web service from the repo on your host of choice, using the
   included `Dockerfile` (or `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   as the start command if the host wants Python-native, not Docker).
3. Set environment variables on the host: `TELEGRAM_BOT_TOKEN`,
   `ANTHROPIC_API_KEY`, `LOG_URL` (set this to `https://<your-deployed-domain>/run.jsonl`).
4. Once deployed, register the webhook (one-time):
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-deployed-domain>/webhook"
   ```
5. Sanity check:
   ```bash
   curl https://<your-deployed-domain>/health
   curl https://<your-deployed-domain>/run.jsonl
   ```
6. Message your bot on Telegram and confirm it replies with a single JSON object.

> Prefer a host that doesn't fully cold-stop between requests (Railway/Fly
> free tiers, or a small paid Render instance) so the grader's message
> isn't dropped by a slow wake-up.

## Testing against the official grading harness

```bash
git clone https://github.com/Jivraj-18/tds-p1-t2-2026-telegram-bot
cd tds-p1-t2-2026-telegram-bot
# add your own questions to evals/questions.json, point it at your bot username
```

## Notes / things to tighten before grading

- `run_python` uses a plain `exec()` — fine for this exercise, but don't
  expose this bot to untrusted public traffic beyond the grader.
- Chat history is kept in-memory (`_history` dict in `app/main.py`) —
  resets on redeploy/restart. Fine for short multi-turn grading sequences;
  swap for Redis/SQLite if you need persistence.
- `build_final_reply()` in `app/main.py` always forces in the correct
  `log_url` itself — the model never has to get that part right.
