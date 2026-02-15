from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models.editorial_session import EditorialSession


class EditorialSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, session_id: str, project_id: str, base_version: int, working_content: str) -> EditorialSession:
        s = EditorialSession(
            session_id=session_id,
            project_id=project_id,
            base_version=base_version,
            current_iteration=1,
            working_content=working_content,
            finalized=False,
        )
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def get(self, session_id: str) -> EditorialSession | None:
        return self.db.get(EditorialSession, session_id)

    def update_iteration(self, *, session_id: str, working_content: str) -> EditorialSession:
        s = self.get(session_id)
        if s is None:
            raise ValueError("Editorial session not found")
        s.current_iteration = int(s.current_iteration) + 1
        s.working_content = working_content
        s.updated_at = datetime.utcnow()
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def finalize(self, session_id: str) -> EditorialSession:
        s = self.get(session_id)
        if s is None:
            raise ValueError("Editorial session not found")
        s.finalized = True
        s.updated_at = datetime.utcnow()
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s
