import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

from app.config import TermsLanguage, get_settings

# One file per language, each a translation of terms.md with the same placeholders.
TERMS_FILES: dict[TermsLanguage, str] = {"en": "terms.md", "es": "terms.es.md"}


@dataclass(frozen=True)
class Terms:
    version: str
    text: str
    language: TermsLanguage


@lru_cache
def get_terms(language: TermsLanguage = "en") -> Terms:
    settings = get_settings()
    path = Path(__file__).with_name(TERMS_FILES[language])
    template = Template(path.read_text(encoding="utf-8"))
    text = template.substitute(
        owner_name=settings.owner_name,
        legal_name=settings.terms_legal_name,
        contact_email=settings.terms_contact_email,
        retention_days=settings.retention_days,
    )
    # Versioned by content, so any wording change requires fresh consent. Each language has
    # its own text, so its own version.
    return Terms(version=hashlib.sha256(text.encode()).hexdigest()[:12], text=text, language=language)
