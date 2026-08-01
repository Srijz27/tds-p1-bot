import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - runtime fallback for stripped containers
    def load_dotenv(*args, **kwargs):
        return False

if "pytest" not in sys.modules and "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
