from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.utils.ids import new_id


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).limit(1)
        return self.db.execute(stmt).scalars().first()

    def create_user(self, *, user_id: str, email: str, password_hash: str) -> User:
        normalized_email = (email or "").strip().lower()
        normalized_user_id = (user_id or "").strip()
        if not normalized_user_id:
            raise ValueError("user_id is required")
        if not normalized_email:
            raise ValueError("email is required")
        if not password_hash:
            raise ValueError("password_hash is required")
        if self.get_by_id(normalized_user_id) is not None:
            raise ValueError("user_id already exists")
        if self.get_by_email(normalized_email) is not None:
            raise ValueError("email already exists")

        created = User(
            user_id=normalized_user_id,
            email=normalized_email,
            password_hash=password_hash,
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created

    def get_or_create_by_email(self, email: str, *, password_hash: str = "") -> User:
        normalized = (email or "").strip().lower()
        if not normalized:
            raise ValueError("email is required")
        existing = self.get_by_email(normalized)
        if existing is not None:
            return existing
        if not password_hash:
            raise ValueError("password_hash is required")
        created = User(user_id=new_id("usr"), email=normalized, password_hash=password_hash)
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created
