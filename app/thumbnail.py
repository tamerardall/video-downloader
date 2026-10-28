"""Fetch the preview thumbnail on the server as a data: URI (the browser never hits the CDN)."""
import base64
import socket
import urllib.request
from urllib.parse import urlparse

from .security import _is_public_ip

MAX_BYTES = 512 * 1024
TYPES = {"image/jpeg", "image/png", "image/webp"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a redirect could point at a private address; don't follow


_opener = urllib.request.build_opener(_NoRedirect)


def _public_host(url: str) -> bool:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        return False
    return all(_is_public_ip(i[4][0]) for i in infos)


def fetch_thumbnail(url: str | None, timeout: float = 5) -> str | None:
    if not url or not _public_host(url):
        return None
    try:
        with _opener.open(url, timeout=timeout) as r:
            ctype = r.headers.get_content_type()
            if r.status != 200 or ctype not in TYPES:
                return None
            data = r.read(MAX_BYTES + 1)
    except Exception:
        return None
    if len(data) > MAX_BYTES:
        return None
    return f"data:{ctype};base64,{base64.b64encode(data).decode()}"
