from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.routes import auth, certificates, contacts, experiences, hackathons, projects
from app.utils.helpers import success_response

app = FastAPI(
    title="Portfolio API",
    description="REST API powering the portfolio's projects, certificates, contact form and admin dashboard. No database - content lives in JSON files, auth is Google/GitHub OAuth with stateless signed sessions.",
    version="2.0.0",
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
    # Never leak internals (stack traces, etc.) to the client.
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


@app.get("/health")
def health_check():
    # No database to check - this is only a liveness probe.
    return success_response({"status": "ok"}, "Service is healthy")
