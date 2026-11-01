import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

from app.config import get_settings


@dataclass(frozen=True)
class Terms:
    version: str
    text: str


@lru_cache
def get_terms() -> Terms:
    settings = get_settings()
    template = Template(Path(__file__).with_name("terms.md").read_text(encoding="utf-8"))
    text = template.substitute(
        legal_name=settings.terms_legal_name,
        contact_email=settings.terms_contact_email,
        retention_days=settings.retention_days,
    )
    # Versioned by content, so any wording change requires fresh consent.
    return Terms(version=hashlib.sha256(text.encode()).hexdigest()[:12], text=text)
