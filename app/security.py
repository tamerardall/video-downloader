"""URL validation and simple rate limiting (SSRF / abuse protection)."""
import ipaddress
import os
import socket
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

DEFAULT_ALLOWED = (
    "tiktok.com,instagram.com,youtube.com,youtu.be,twitter.com,x.com,"
    "facebook.com,fb.watch,reddit.com,vimeo.com,pinterest.com,twitch.tv"
)
ALLOWED_DOMAINS = tuple(
    d.strip().lower()
    for d in os.environ.get("ALLOWED_DOMAINS", DEFAULT_ALLOWED).split(",")
    if d.strip()
)
MAX_URL_LEN = 2048


class InvalidURL(ValueError):
    pass


def _domain_allowed(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_global and not addr.is_multicast


def validate_url(url: str, resolve: bool = True) -> str:
    if not url or len(url) > MAX_URL_LEN:
        raise InvalidURL("Invalid URL.")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise InvalidURL("Only http/https URLs are supported.")
    if parsed.username or parsed.password:
        raise InvalidURL("URLs with credentials are not allowed.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise InvalidURL("Invalid URL.")
    if not _domain_allowed(host):
        raise InvalidURL("This site is not supported (see ALLOWED_DOMAINS).")
    if resolve:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise InvalidURL("Could not resolve the host.")
        if not all(_is_public_ip(i[4][0]) for i in infos):
            raise InvalidURL("Local/private addresses are not allowed.")
    return url.strip()


class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
