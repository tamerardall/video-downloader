"""Start the server: `python -m app` (same command on Linux, macOS and Windows).

HOST and PORT come from the environment or .env (defaults: 127.0.0.1:8000).
"""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
