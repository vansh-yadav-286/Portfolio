from fastapi import APIRouter, HTTPException, status

from app.schemas import LoginRequest, Token
from app.security import create_access_token, verify_admin_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest):
    if not verify_admin_credentials(credentials.email, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(subject=credentials.email)
    return Token(access_token=access_token)
