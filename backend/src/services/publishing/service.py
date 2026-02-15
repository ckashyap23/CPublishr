from sqlalchemy.orm import Session

from src.contracts.prd import DistributionRequest, DistributionResponse
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.db.repositories.publish_repository import PublishRepository
from src.utils.ids import new_id


class PublishingService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.content = ContentRepository(db)
        self.publish = PublishRepository(db)

    def create_job(self, payload: DistributionRequest) -> DistributionResponse:
        DistributionRequest.model_validate(payload)
        project_id = (payload.content_payload or {}).get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("content_payload.project_id is required")
        self.projects.get_or_create(project_id)

        latest_output = self.content.get_latest_platform_output(project_id, payload.platform)
        if latest_output is None:
            raise ValueError(f"No generated platform output found for project '{project_id}' and platform '{payload.platform}'")

        external_id = new_id("ext")
        self.publish.create_job(
            publish_job_id=new_id("pub"),
            project_id=project_id,
            platform=payload.platform,
            status="published",
            scheduled_time=None,
            external_id=external_id,
            platform_output_id=latest_output.output_id,
            payload_snapshot={
                "project_id": project_id,
                "platform": payload.platform,
                "platform_output_id": latest_output.output_id,
                "format_type": latest_output.format_type,
                "content": latest_output.content,
            },
        )
        return DistributionResponse(status="published", external_id=external_id)
