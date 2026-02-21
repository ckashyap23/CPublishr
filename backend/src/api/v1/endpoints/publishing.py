from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.contracts.prd import DistributionRequest, DistributionResponse
from src.services.publishing.service import PublishingService

router = APIRouter()


@router.post("/jobs", response_model=DistributionResponse)
def create_publish_job(
    payload: DistributionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DistributionResponse:
    try:
        return PublishingService(db, user_id=user_id).create_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
