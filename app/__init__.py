"""Load settings from the project's .env file before any module reads os.environ."""
import os
from pathlib import Path

if not os.environ.get("VD_NO_DOTENV"):  # tests set this so a local .env can't interfere
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
