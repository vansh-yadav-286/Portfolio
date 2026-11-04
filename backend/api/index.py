# Vercel's Python runtime looks for an ASGI/WSGI `app` object in this file
# and serves it directly - no uvicorn process needed in production. Local
# dev still runs `uvicorn app.main:app --reload` from backend/ as before.
from app.main import app  # noqa: F401
