from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.voice_profile import VoiceProfile, VoiceProfilePlatform
from src.utils.ids import new_id


class VoiceProfileRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def list_profiles(self) -> list[VoiceProfile]:
        stmt = select(VoiceProfile).where(VoiceProfile.user_id == self.user_id).order_by(VoiceProfile.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_profile(self, voice_profile_id: str) -> VoiceProfile | None:
        stmt = (
            select(VoiceProfile)
            .where(VoiceProfile.user_id == self.user_id)
            .where(VoiceProfile.voice_profile_id == voice_profile_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def list_profile_platforms(self, voice_profile_id: str) -> list[str]:
        stmt = (
            select(VoiceProfilePlatform.platform)
            .where(VoiceProfilePlatform.user_id == self.user_id)
            .where(VoiceProfilePlatform.voice_profile_id == voice_profile_id)
            .order_by(VoiceProfilePlatform.platform.asc())
        )
        return [str(x) for x in self.db.execute(stmt).scalars().all()]

    def create_profile(
        self,
        *,
        name: str,
        description: str | None = None,
        rules_json: dict | None = None,
        platforms: list[str] | None = None,
        is_default: bool = False,
    ) -> VoiceProfile:
        if is_default:
            existing_defaults = (
                self.db.query(VoiceProfile)
                .filter(VoiceProfile.user_id == self.user_id)
                .filter(VoiceProfile.is_default.is_(True))
                .all()
            )
            for row in existing_defaults:
                row.is_default = False
                self.db.add(row)
        profile = VoiceProfile(
            voice_profile_id=new_id("vp"),
            user_id=self.user_id,
            name=name.strip(),
            description=(description or "").strip() or None,
            rules_json=rules_json or {},
            is_default=bool(is_default),
        )
        self.db.add(profile)
        self.db.flush()
        for p in platforms or []:
            platform = str(p).strip().lower()
            if not platform:
                continue
            self.db.add(
                VoiceProfilePlatform(
                    row_id=new_id("vpp"),
                    voice_profile_id=profile.voice_profile_id,
                    user_id=self.user_id,
                    platform=platform,
                )
            )
        self.db.commit()
        self.db.refresh(profile)
        return profile
