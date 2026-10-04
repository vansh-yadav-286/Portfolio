from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.database.database import SessionLocal
from app.routes import analytics, auth, certificates, contacts, projects
from app.services.auth_service import ensure_admin_seeded
from app.utils.helpers import success_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_admin_seeded(db, settings.admin_email, settings.admin_password)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Portfolio API",
    description="REST API powering the portfolio's projects, certificates, contact form and admin dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return _rate_limit_exceeded_handler(request, exc)


@app.exception_handler(HTTPException)
async def api_http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        # "ctx" can hold raw exception objects (from custom validators), which are not JSON-serializable.
        content={
            "success": False,
            "message": "Validation error",
            "errors": [{k: v for k, v in err.items() if k != "ctx"} for err in exc.errors()],
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    # Never leak internals (stack traces, DB errors) to the client.
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error"},
    )


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(certificates.router)
app.include_router(contacts.router)
app.include_router(analytics.router)


@app.get("/health")
def health_check():
    return success_response({"status": "ok"}, "Service is healthy")
