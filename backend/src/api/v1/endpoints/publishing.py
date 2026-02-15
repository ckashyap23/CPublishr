from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import DistributionRequest, DistributionResponse
from src.services.publishing.service import PublishingService

router = APIRouter()


@router.post("/jobs", response_model=DistributionResponse)
def create_publish_job(payload: DistributionRequest, db: Session = Depends(get_db)) -> DistributionResponse:
    try:
        return PublishingService(db).create_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
