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


class CloudRunSettings(BaseSettings):
    """How the agent reaches cloud-run's signed /internal/* endpoints (ADR-2, ADR-9)."""

    model_config = _CONFIG

    # With it set, facts come from cloud-run and transcripts go to it. Without it, facts come
    # from the local seed file and transcripts aren't sent, for local development.
    cloud_run_url: str = ""
    # Shared with cloud-run, which checks the agent's signed requests (ADR-9).
    agent_signing_secret: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def _secret_when_fetching(self) -> Self:
        if self.cloud_run_url and len(self.agent_signing_secret.get_secret_value()) < 32:
            raise ValueError("AGENT_SIGNING_SECRET needs 32+ characters when CLOUD_RUN_URL is set")
        return self


class FactsSettings(CloudRunSettings):
    """Where the facts come from (facts.py, ADR-21). Read at each call start."""

    facts_path: Path = DEFAULT_FACTS_PATH


class AgentSettings(BaseSettings):
    """The voice and avatar. Read once at startup, so a missing value stops the agent."""

    model_config = _CONFIG

    # Explicit dispatch (U3): with a name set, the agent only joins rooms it is dispatched to.
    livekit_agent_name: str = "portfolio-twin"
    # No default voice: the twin must never fall back to a stock voice by accident.
    elevenlabs_voice_id: str
    # Lee's Spanish voice. Required for the same reason, because the twin is bilingual (ADR-20).
    elevenlabs_spanish_voice_id: str
    # Stock voices that speak only while Lee's voice is failing, so the visitor hears a
    # different voice instead of silence. Deliberate fallbacks, never a silent default for
    # Lee's own voice above. Both are male and speak English and Spanish.
    # First an ElevenLabs library voice, for a problem with Lee's cloned voice alone.
    backup_elevenlabs_voice_id: str = "zs057lc0shdaAFXkm2Fm"
    # Then a voice on another provider, for when ElevenLabs itself is down. LiveKit Inference,
    # so no extra key. Cartesia Sonic 3 "Blake".
    last_resort_tts_model: str = "cartesia/sonic-3"
    last_resort_tts_voice: str = "a167e0f3-df7e-4d52-a9c3-f949145efdab"
    tavus_api_key: SecretStr
    tavus_face_id: str
