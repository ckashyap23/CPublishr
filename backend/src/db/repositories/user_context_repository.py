from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.user_context_memory import UserContextMemory
from src.utils.ids import new_id


class UserContextRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def get(self) -> UserContextMemory | None:
        stmt = select(UserContextMemory).where(UserContextMemory.user_id == self.user_id).limit(1)
        return self.db.execute(stmt).scalars().first()

    def upsert(
        self,
        *,
        last_project_id: str | None = None,
        last_view: str | None = None,
        state_json: dict | None = None,
    ) -> UserContextMemory:
        row = self.get()
        if row is None:
            row = UserContextMemory(
                memory_id=new_id("mem"),
                user_id=self.user_id,
            )
        if last_project_id is not None:
            row.last_project_id = last_project_id
        if last_view is not None:
            row.last_view = last_view
        if state_json is not None:
            row.state_json = state_json
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
