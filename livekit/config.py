"""The agent's own config, validated by pydantic-settings.

agent.py loads .env into the process first, because the LiveKit SDK and its plugins read their
own keys from the environment (LIVEKIT_*, ELEVEN_API_KEY, GOOGLE_API_KEY). These classes never
read .env themselves, so tests don't see a developer's real values.

Validation errors hide their input, so a bad secret never ends up in a log (ADR-14).
"""

from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FACTS_PATH = Path(__file__).parent / "facts" / "lee.yaml"

_CONFIG = SettingsConfigDict(hide_input_in_errors=True)


class FactsSettings(BaseSettings):
    """Where the facts come from (facts.py, ADR-21). Read at each call start."""

    model_config = _CONFIG

    # With it set, facts come from cloud-run. Without it, from the local seed file.
    cloud_run_url: str = ""
    facts_path: Path = DEFAULT_FACTS_PATH
    # Shared with cloud-run, which checks the agent's signed requests (ADR-9).
    agent_signing_secret: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def _secret_when_fetching(self) -> Self:
        if self.cloud_run_url and len(self.agent_signing_secret.get_secret_value()) < 32:
            raise ValueError("AGENT_SIGNING_SECRET needs 32+ characters when CLOUD_RUN_URL is set")
        return self


class AgentSettings(BaseSettings):
    """The voice and avatar. Read once at startup, so a missing value stops the agent."""

    model_config = _CONFIG

    # Explicit dispatch (U3): with a name set, the agent only joins rooms it is dispatched to.
    livekit_agent_name: str = "portfolio-twin"
    # No default voice: the twin must never fall back to a stock voice by accident.
    elevenlabs_voice_id: str
    tavus_api_key: SecretStr
    tavus_face_id: str
