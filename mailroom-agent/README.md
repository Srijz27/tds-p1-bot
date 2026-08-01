# Mailroom Agent

This repo contains a small Flask skeleton for the mailroom evaluation flow.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Routes

- POST `/mailroom`

## Notes

- The repository keeps SQLite state in `mailroom.db`.
- The `.env` file is intentionally not committed.
