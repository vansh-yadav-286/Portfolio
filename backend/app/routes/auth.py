from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserLogin, UserOut, UserRegister
from app.services.auth_service import authenticate_user, issue_token, register_user
from app.utils.helpers import success_response


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user = register_user(db, payload)
    return success_response(
        UserOut.model_validate(user),
        "Account created successfully",
        status_code=201,
    )


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, payload)
    token = Token(access_token=issue_token(user))

    return success_response(
        token.model_dump(),
        "Login successful",
    )


@router.post("/token")
@limiter.limit("5/minute")
def token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    payload = UserLogin(
        email=form_data.username,
        password=form_data.password,
    )

    user = authenticate_user(db, payload)
    access_token = issue_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(
        UserOut.model_validate(current_user),
        "Current user",
    )


@router.post("/logout")
def logout():
    # JWTs are stateless; the client discards the token.
    # Documented here for API completeness / a future token-blacklist
    # if one becomes necessary.
    return success_response(None, "Logged out successfully")