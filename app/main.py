import asyncio
import hmac
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .security import InvalidURL, RateLimiter, validate_url

STATIC = Path(__file__).parent / "static"
MAX_FILESIZE = 500 * 1024 * 1024  # 500 MB
limiter = RateLimiter(limit=10, window=60)
API_TOKEN = os.environ.get("API_TOKEN", "")

app = FastAPI(title="Video Downloader", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    return resp


class UrlBody(BaseModel):
    url: str


def _check(request: Request, url: str) -> str:
    if API_TOKEN:
        sent = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(sent.encode(), API_TOKEN.encode()):
            raise HTTPException(401, "Geçersiz veya eksik anahtar.")
    ip = request.client.host if request.client else "unknown"
    if not limiter.allow(ip):
        raise HTTPException(429, "Çok fazla istek, biraz bekleyin.")
    try:
        return validate_url(url)
    except InvalidURL as e:
        raise HTTPException(400, str(e))


def _opts(**extra):
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_FILESIZE,
        "socket_timeout": 20,
        **extra,
    }


@app.post("/api/info")
async def info(body: UrlBody, request: Request):
    url = _check(request, body.url)

    def run():
        with yt_dlp.YoutubeDL(_opts(skip_download=True)) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        data = await asyncio.to_thread(run)
    except Exception:
        raise HTTPException(422, "Video bilgisi alınamadı.")
    return {
        "title": data.get("title"),
        "uploader": data.get("uploader"),
        "duration": data.get("duration"),
        "extractor": data.get("extractor_key"),
    }


@app.post("/api/download")
async def download(body: UrlBody, request: Request, bg: BackgroundTasks):
    url = _check(request, body.url)
    tmp = Path(tempfile.mkdtemp(prefix="vd_"))

    def run():
        opts = _opts(
            outtmpl=str(tmp / "%(id)s.%(ext)s"),
            format="bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            merge_output_format="mp4",
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

    try:
        await asyncio.to_thread(run)
        files = [f for f in tmp.iterdir() if f.is_file()]
        if not files:
            raise RuntimeError("no file")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return JSONResponse({"detail": "İndirme başarısız."}, status_code=422)

    bg.add_task(shutil.rmtree, tmp, True)
    f = files[0]
    media = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    return FileResponse(f, filename=f.name, media_type=media)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
