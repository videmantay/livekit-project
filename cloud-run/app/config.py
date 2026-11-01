from functools import lru_cache

from dotenv import load_dotenv
from pydantic import SecretStr
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

    terms_legal_name: str
    terms_contact_email: str

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
