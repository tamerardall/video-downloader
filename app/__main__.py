"""Start the server: `python -m app` (same command on Linux, macOS and Windows).

HOST and PORT come from the environment or .env (defaults: 127.0.0.1:8000).
On the first run .env is created from .env.example.
"""
import os
import shutil
from pathlib import Path

import uvicorn

ENV = Path(__file__).resolve().parent.parent / ".env"

if __name__ == "__main__":
    if not ENV.exists():
        # .env.example only holds the defaults, so nothing needs reloading
        shutil.copy(ENV.with_name(".env.example"), ENV)
        print(f"Created {ENV} from .env.example; edit it to change settings.")
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
