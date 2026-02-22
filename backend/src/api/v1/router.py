from fastapi import APIRouter

from src.api.v1.endpoints import artifacts, auth, health, platform_outputs, projects, publishing, versions, voice_profiles, workflows

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(voice_profiles.router, prefix="/voice-profiles", tags=["voice-profiles"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(versions.router, prefix="/versions", tags=["versions"])
api_router.include_router(platform_outputs.router, prefix="/platform-outputs", tags=["platform-outputs"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["publishing"])
