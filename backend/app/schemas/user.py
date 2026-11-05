from pydantic import BaseModel, EmailStr


class MeOut(BaseModel):
    email: EmailStr
    name: str
    role: str
    provider: str
    # Echoed back so the frontend can attach it as X-CSRF-Token on mutating
    # requests - see core/dependencies.py::verify_csrf. Not a secret: it only
    # proves the request came from a page that could read this response, i.e.
    # the same browser that holds the (HttpOnly, unreadable) session cookie.
    csrf_token: str
