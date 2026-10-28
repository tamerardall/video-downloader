import asyncio
import hmac
import logging
import mimetypes
import os
import re
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .security import InvalidURL, RateLimiter, validate_url
from .thumbnail import fetch_thumbnail

log = logging.getLogger("uvicorn.error")  # uvicorn terminaline yazar
ANSI = re.compile(r"\x1b\[[0-9;]*m")
URL_IN_TEXT = re.compile(r"https?://\S+")
STATIC = Path(__file__).parent / "static"
MAX_FILESIZE = 500 * 1024 * 1024  # 500 MB
limiter = RateLimiter(limit=10, window=60)
API_TOKEN = os.environ.get("API_TOKEN", "")
# Instagram vb. giriş isteyen siteler için: Netscape formatında cookies.txt yolu
# ya da çerezlerin okunacağı tarayıcı adı (firefox, chrome, ...).
COOKIES_FILE = os.environ.get("COOKIES_FILE", "")
COOKIES_FROM_BROWSER = os.environ.get("COOKIES_FROM_BROWSER", "")
LOGIN_HINTS = ("--cookies", "login required", "log in", "empty media response")

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
        # Kısayol başarıyı (mp4) hatadan (json) dosya uzantısıyla ayırıyor
        resp.headers["Content-Disposition"] = 'inline; filename="hata.json"'
    return resp


class UrlBody(BaseModel):
    url: str


@app.exception_handler(RequestValidationError)
async def bad_body(request: Request, exc: RequestValidationError):
    # Kısayol yanlış gövde gönderirse (JSON değil, "url" alanı yok...) terminalde görünsün
    log.warning("Geçersiz istek gövdesi: %s", exc.errors())
    return JSONResponse({"detail": "İstek gövdesi JSON ve içinde 'url' alanı olmalı."},
                        status_code=422)


def _check(request: Request, url: str) -> str:
    ip = request.client.host if request.client else "unknown"
    if API_TOKEN:
        sent = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(sent.encode(), API_TOKEN.encode()):
            log.warning("Geçersiz veya eksik anahtar (%s)", ip)
            raise HTTPException(401, "Geçersiz veya eksik anahtar.")
    if not limiter.allow(ip):
        log.warning("İstek sınırı aşıldı (%s)", ip)
        raise HTTPException(429, "Çok fazla istek, biraz bekleyin.")
    # Paylaşım sayfası bağlantıyı açıklama metniyle birlikte gönderebiliyor
    found = URL_IN_TEXT.search(url)
    if found:
        url = found.group(0)
    try:
        return validate_url(url)
    except InvalidURL as e:
        log.warning("URL reddedildi: %s (%r)", e, url[:200])
        raise HTTPException(400, str(e))


def _opts(**extra):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_FILESIZE,
        "socket_timeout": 20,
        **extra,
    }
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    if COOKIES_FROM_BROWSER:
        # "brave" ya da "brave:/profil/yolu" (Flatpak tarayıcılar için)
        browser, _, profile = COOKIES_FROM_BROWSER.partition(":")
        opts["cookiesfrombrowser"] = (browser, profile or None)
    return opts


def _error(e: Exception, default: str) -> str:
    msg = ANSI.sub("", str(e)).strip().removeprefix("ERROR:").strip()
    log.warning("%s %s", default, msg)
    if any(h in msg.lower() for h in LOGIN_HINTS):
        default = ("Bu site giriş yapmayı istiyor. Sunucuda COOKIES_FILE veya "
                   "COOKIES_FROM_BROWSER ile çerez tanımlayın (README'ye bakın).")
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
        raise HTTPException(422, _error(e, "Video bilgisi alınamadı."))
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
            format="bv*+ba/b",
            # iPhone Fotoğraflar VP9/AV1 kaydetmiyor: H.264 + AAC tercih edilir
            format_sort=["vcodec:h264", "acodec:aac", "ext:mp4:m4a"],
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
        return JSONResponse({"detail": _error(e, "İndirme başarısız.")}, status_code=422)

    bg.add_task(shutil.rmtree, tmp, True)
    f = files[0]
    log.info("İndirildi: %s (%.1f MB, görüntü %s, ses %s)", f.name,
             f.stat().st_size / 1e6, data.get("vcodec"), data.get("acodec"))
    media = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    return FileResponse(f, filename=f.name, media_type=media)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
