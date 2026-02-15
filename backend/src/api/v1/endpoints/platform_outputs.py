from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import PlatformOutputEntity, PlatformOutputListResponse
from src.db.repositories.content_repository import ContentRepository

router = APIRouter()


@router.get("/{project_id}", response_model=PlatformOutputListResponse)
def list_platform_outputs(project_id: str, db: Session = Depends(get_db)) -> PlatformOutputListResponse:
    outputs = ContentRepository(db).list_platform_outputs(project_id)
    return PlatformOutputListResponse(project_id=project_id, outputs=[PlatformOutputEntity(platform=o.platform, format_type=o.format_type, content=o.content, optimized=o.optimized) for o in outputs])
