import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if "pytest" not in sys.modules and "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
