import os
import json

from dotenv import load_dotenv

load_dotenv()


def decide(dossier):
    """Return a safe fallback decision structure for now.

    The actual production version should call the model with a strict system
    prompt and validate the returned JSON against one of the allowed action
    schemas.
    """
    if isinstance(dossier, dict) and "prompt" in dossier:
        text = str(dossier.get("prompt", "")).lower()
        if "ignore" in text or "system" in text:
            return {
                "type": "quarantine_item",
                "reason": "prompt injection-like content detected",
            }

    return {
        "type": "request_confirmation",
        "reason": "safe fallback decision used in scaffold mode",
    }


def call_model(dossier):
    return decide(dossier)
