"""URL validation and simple rate limiting (SSRF / abuse protection)."""
import ipaddress
import os
import socket
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

# Empty (the default) means every public site is allowed; set it to restrict.
def _parse_domains(raw: str | None) -> tuple[str, ...]:
    return tuple(d.strip().lower() for d in (raw or "").split(",") if d.strip())


ALLOWED_DOMAINS = _parse_domains(os.environ.get("ALLOWED_DOMAINS"))
MAX_URL_LEN = 2048


class InvalidURL(ValueError):
    pass


def _domain_allowed(host: str) -> bool:
    if not ALLOWED_DOMAINS:
        return True
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_global and not addr.is_multicast


def _check_public_http(url: str, resolve: bool, check_site: bool) -> str:
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
    if check_site and not _domain_allowed(host):
        raise InvalidURL("This site is not supported (see ALLOWED_DOMAINS).")
    if resolve:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise InvalidURL("Could not resolve the host.")
        if not all(_is_public_ip(i[4][0]) for i in infos):
            raise InvalidURL("Local/private addresses are not allowed.")
    return url.strip()


def validate_url(url: str, resolve: bool = True) -> str:
    return _check_public_http(url, resolve, check_site=True)


def check_media_url(url: str, resolve: bool = True) -> str:
    """Validate a media URL found by the extractor (CDNs live on other domains,
    so ALLOWED_DOMAINS is not applied)."""
    return _check_public_http(url, resolve, check_site=False)


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
