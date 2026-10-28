import asyncio
import hmac
import logging
import mimetypes
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .security import InvalidURL, RateLimiter, validate_url
from .thumbnail import fetch_thumbnail

log = logging.getLogger("uvicorn.error")  # shows up in the uvicorn terminal
ANSI = re.compile(r"\x1b\[[0-9;]*m")
URL_IN_TEXT = re.compile(r"https?://\S+")
STATIC = Path(__file__).parent / "static"
MAX_FILESIZE = 500 * 1024 * 1024  # 500 MB
limiter = RateLimiter(limit=10, window=60)
API_TOKEN = os.environ.get("API_TOKEN", "")
# For sites that require login (Instagram, ...): a Netscape cookies.txt path, or the
# browser to read cookies from ("firefox", or "browser:/profile/path" for custom profiles).
COOKIES_FILE = os.environ.get("COOKIES_FILE", "")
COOKIES_FROM_BROWSER = os.environ.get("COOKIES_FROM_BROWSER", "")
LOGIN_HINTS = ("--cookies", "login required", "log in", "empty media response")
# JS runtime yt-dlp needs for YouTube (pip "deno" package). The server may run without the
# venv activated, so .venv/bin (Scripts on Windows) isn't on PATH; look it up explicitly.
DENO = shutil.which("deno", path=str(Path(sys.executable).parent))
# Merges video and audio. Prefer a system ffmpeg (newer, comes with ffprobe), otherwise
# use the static binary from the imageio-ffmpeg package.
FFMPEG = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
FORMAT = "bv*+ba/b"
# iPhone Photos won't save VP9/AV1, so prefer H.264 + AAC. "res" must come before the
# audio key, otherwise YouTube's old muxed 360p file (it has audio) beats 1080p video+audio.
FORMAT_SORT = ["vcodec:h264", "res", "acodec:aac", "ext:mp4:m4a"]

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
    if resp.headers.get("content-type", "").startswith("application/json"):
        # The iOS Shortcut tells success (mp4) from errors (json) by file extension
        resp.headers["Content-Disposition"] = 'inline; filename="error.json"'
    return resp


class UrlBody(BaseModel):
    url: str


@app.exception_handler(RequestValidationError)
async def bad_body(request: Request, exc: RequestValidationError):
    # Log malformed bodies (not JSON, no "url" field...) so Shortcut setup mistakes are visible
    log.warning("Invalid request body: %s", exc.errors())
    return JSONResponse({"detail": "Request body must be JSON with a 'url' field."},
                        status_code=422)


def _check(request: Request, url: str) -> str:
    ip = request.client.host if request.client else "unknown"
    if API_TOKEN:
        sent = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(sent.encode(), API_TOKEN.encode()):
            log.warning("Invalid or missing API token (%s)", ip)
            raise HTTPException(401, "Invalid or missing API token.")
    if not limiter.allow(ip):
        log.warning("Rate limit exceeded (%s)", ip)
        raise HTTPException(429, "Too many requests, please wait a minute.")
    # Share sheets may send the link together with caption text
    found = URL_IN_TEXT.search(url)
    if found:
        url = found.group(0)
    try:
        return validate_url(url)
    except InvalidURL as e:
        log.warning("URL rejected: %s (%r)", e, url[:200])
        raise HTTPException(400, str(e))


def _opts(**extra):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_FILESIZE,
        "socket_timeout": 20,
        "ffmpeg_location": FFMPEG,
        **extra,
    }
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    if COOKIES_FROM_BROWSER:
        # "firefox" or "firefox:/profile/path"; splits on the first colon only, so
        # Windows paths like "firefox:C:\Users\me\profile" stay intact
        browser, _, profile = COOKIES_FROM_BROWSER.partition(":")
        opts["cookiesfrombrowser"] = (browser, profile or None)
    if DENO:
        opts["js_runtimes"] = {"deno": {"path": DENO}}
    return opts


def _error(e: Exception, default: str) -> str:
    msg = ANSI.sub("", str(e)).strip().removeprefix("ERROR:").strip()
    log.warning("%s %s", default, msg)
    if any(h in msg.lower() for h in LOGIN_HINTS):
        default = ("This site requires login. Set COOKIES_FROM_BROWSER or COOKIES_FILE "
                   "on the server (see README).")
    return f"{default} ({msg[:300]})" if msg else default


@app.post("/api/info")
async def info(body: UrlBody, request: Request):
    url = _check(request, body.url)

    def run():
        with yt_dlp.YoutubeDL(_opts(skip_download=True)) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        data = await asyncio.to_thread(run)
    except Exception as e:
        raise HTTPException(422, _error(e, "Could not get video info."))
    return {
        "title": data.get("title"),
        "uploader": data.get("uploader"),
        "duration": data.get("duration"),
        "extractor": data.get("extractor_key"),
        "thumbnail": await asyncio.to_thread(fetch_thumbnail, data.get("thumbnail")),
    }


@app.post("/api/download")
async def download(body: UrlBody, request: Request, bg: BackgroundTasks):
    url = _check(request, body.url)
    tmp = Path(tempfile.mkdtemp(prefix="vd_"))

    def run():
        opts = _opts(
            outtmpl=str(tmp / "%(id)s.%(ext)s"),
            format=FORMAT,
            format_sort=FORMAT_SORT,
            merge_output_format="mp4",
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=True)

    try:
        data = await asyncio.to_thread(run) or {}
        files = [f for f in tmp.iterdir() if f.is_file()]
        if not files:
            raise RuntimeError("no file")
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return JSONResponse({"detail": _error(e, "Download failed.")}, status_code=422)

    bg.add_task(shutil.rmtree, tmp, True)
    f = files[0]
    log.info("Downloaded: %s (%.1f MB, video %s, audio %s)", f.name,
             f.stat().st_size / 1e6, data.get("vcodec"), data.get("acodec"))
    media = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    return FileResponse(f, filename=f.name, media_type=media)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
