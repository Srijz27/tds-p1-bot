import os

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id: int, text: str) -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    requests.post(f"{TG_API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)


def set_webhook(url: str) -> dict:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    r = requests.get(f"{TG_API}/setWebhook", params={"url": url}, timeout=15)
    return r.json()
