from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

# Exports .env to the process too, so Google clients see GOOGLE_APPLICATION_CREDENTIALS.
load_dotenv()


class Settings(BaseSettings):
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: SecretStr
    livekit_agent_name: str = "portfolio-twin"

    firebase_project_id: str
    allowed_origins: str = "http://localhost:5173"

    # The owner's display name, used in the terms and the summary prompt (ADR-23).
    owner_name: str
    terms_legal_name: str
    terms_contact_email: str

    # The one Google account allowed into admin (ADR-10). From config, never code.
    admin_email: str
    # Shared with the agent. Signs its requests to /internal/* (ADR-9).
    agent_signing_secret: SecretStr = Field(min_length=32)

    # Call summaries, through Vertex AI with the service's own identity. No API key (ADR-9).
    gemini_model: str = "gemini-3.5-flash"
    vertex_location: str = "global"

    # Link-only notification email after each call (A6). Skipped when SMTP_HOST is unset.
    admin_url: str = "http://localhost:5173/admin"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    notify_from: str = ""

    retention_days: int = 90
    token_ttl_seconds: int = 300
    max_session_minutes: int = 15
    rate_limit_per_minute: int = 10

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
