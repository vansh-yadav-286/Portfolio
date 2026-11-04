from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    # Behind Render's proxy, request.client is the proxy, so every visitor would
    # share one rate-limit bucket. The proxy appends the real client IP to
    # X-Forwarded-For; the rightmost entry is the one it added, so that is what we
    # trust (the leftmost entries are supplied by the client and can be spoofed).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip)
