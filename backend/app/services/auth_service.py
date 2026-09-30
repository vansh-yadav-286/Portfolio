from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserLogin, UserRegister
from app.utils.helpers import api_error


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise api_error("An account with this email already exists", status_code=409)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLogin) -> User:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise api_error("Invalid email or password", status_code=401)
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=user.email, role=user.role.value)


def ensure_admin_seeded(db: Session, admin_email: str, admin_password: str) -> None:
    admin = db.query(User).filter(User.email == admin_email).first()
    if admin:
        return
    admin = User(
        name="Admin",
        email=admin_email,
        password_hash=hash_password(admin_password),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
