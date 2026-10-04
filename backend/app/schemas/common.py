from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator


def _check_url(value: str | None) -> str | None:
    # Accepts http(s) links and relative paths (e.g. "assets/logos/x.jpg").
    # Rejects other schemes such as javascript: or data:, which would run or
    # load untrusted content when rendered as a link or image on the public site.
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith("//"):
        raise ValueError("Protocol-relative URLs are not allowed")
    scheme = urlparse(value).scheme.lower()
    if scheme not in ("", "http", "https"):
        raise ValueError("URL must start with http:// or https://, or be a relative path")
    return value


SafeUrl = Annotated[str | None, AfterValidator(_check_url)]
