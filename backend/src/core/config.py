from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CPublishr API"
    env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cors_allow_origins: str = (
        "http://127.0.0.1:3000,http://localhost:3000,"
        "http://127.0.0.1:3001,http://localhost:3001,"
        "http://127.0.0.1:5173,http://localhost:5173"
    )

    # DB bootstrap behavior
    db_auto_create: bool = True

    # Auth
    auth_jwt_secret: str = "change-me-in-env"
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 60 * 24

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_model_name: str = "gpt-4o-mini"
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_subscription_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    artifact_text_llm_enabled: bool = False

    # Image generation (DALL-E 3); empty = simulated mode
    azure_openai_image_deployment: str = ""
    azure_openai_image_api_version: str = "2024-02-15-preview"

    # Azure Blob storage for voice profile dataset ingestion
    azure_storage_connection_string: str = ""
    azure_profile_entries_container: str = "profile-entries"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
