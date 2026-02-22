from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.core.security import create_access_token, hash_password, verify_password
from src.db.repositories.user_repository import UserRepository
from src.schemas.auth import AuthTokenResponse, AuthUserResponse, LoginRequest, SignUpRequest

router = APIRouter()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


@router.post("/signup", response_model=AuthTokenResponse)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    repo = UserRepository(db)
    requested_user_id = (payload.user_id or "").strip()
    normalized = _normalize_email(payload.email)
    if not requested_user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if "@" not in normalized:
        raise HTTPException(status_code=400, detail="Valid email is required")
    if repo.get_by_id(requested_user_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User ID already exists")
    if repo.get_by_email(normalized) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = repo.create_user(
        user_id=requested_user_id,
        email=normalized,
        password_hash=hash_password(payload.password),
    )
    token = create_access_token(user_id=user.user_id)
    return AuthTokenResponse(
        access_token=token,
        user=AuthUserResponse(user_id=user.user_id, email=user.email),
        default_voice_profile_id=None,
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    requested_user_id = (payload.user_id or "").strip()
    user = UserRepository(db).get_by_id(requested_user_id)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID or password")
    token = create_access_token(user_id=user.user_id)
    return AuthTokenResponse(
        access_token=token,
        user=AuthUserResponse(user_id=user.user_id, email=user.email),
        default_voice_profile_id=None,
    )


@router.get("/me", response_model=AuthUserResponse)
def me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)) -> AuthUserResponse:
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthUserResponse(user_id=user.user_id, email=user.email)
