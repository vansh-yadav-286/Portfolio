import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.database.database import SessionLocal, check_database_connection
from app.routes import analytics, auth, certificates, contacts, experiences, hackathons, projects
from app.services.auth_service import ensure_admin_seeded
from app.utils.helpers import success_response

logger = logging.getLogger(__name__)


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
    allow_origins=settings.frontend_origins,
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
app.include_router(hackathons.router)
app.include_router(experiences.router)
app.include_router(contacts.router)
app.include_router(analytics.router)


@app.get("/health")
def health_check():
    # Runs SELECT 1 against Postgres, so "ok" means the database answered, not just that DATABASE_URL is set.
    try:
        check_database_connection()
    except Exception:
        logger.exception("Health check could not reach the database")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Database unreachable",
                "data": {"status": "degraded", "database": "unreachable"},
            },
        )
    return success_response({"status": "ok", "database": "connected"}, "Service is healthy")
