"""The twin's two languages, English and Spanish, with the fixed lines and prompt rules (ADR-20).

The twin is bilingual because Lee is: Spanish matches Lee's real, fluent level. Portuguese is
never generated, because Lee's Portuguese is about B2 and the AI's would sound far better.

A call starts in the language the visitor agreed to the terms in, which cloud-run sends in the
dispatch metadata, and English otherwise. Speech recognition detects the language by itself, so a
request made in Spanish is understood before any switch. The set_language tool changes the voice,
because the Spanish voice is a separate ElevenLabs voice.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "es"]

LANGUAGE_NAMES: dict[Language, str] = {"en": "English", "es": "Spanish"}


def start_language(metadata: dict) -> Language:
    """Spanish when the visitor agreed to the Spanish terms, else English."""
    return "es" if metadata.get("terms_language") == "es" else "en"


class LanguageSwitch:
    """The call's current language. Switching changes the voice through `switch_voice`."""

    def __init__(
        self, start: Language = "en", switch_voice: Callable[[Language], None] | None = None
    ) -> None:
        self._switch_voice = switch_voice
        self.current: Language = start

    def switch(self, language: Language) -> str:
        """Returns the tool result the model reads before it replies."""
        name = LANGUAGE_NAMES[language]
        if language == self.current:
            return f"Already speaking {name}. Reply in {name}."
        if self._switch_voice is not None:
            self._switch_voice(language)
        self.current = language
        return f"Switched to {name}. Reply in {name} from now on."


@dataclass(frozen=True)
class Lines:
    blocked: str
    no_facts: str
    time_up: str


# Spoken as written, in the call's current language. The Spanish ones are drafts for Lee to
# check, like the Spanish greetings in persona.py.
LINES: dict[Language, Lines] = {
    "en": Lines(
        blocked="That's not something I can talk about, but I'm happy to tell you about Lee's work.",
        no_facts=(
            "Hi, I'm Lee's AI twin. Sorry, I can't answer questions right now because something's "
            "wrong on my end. Please try again later, or reach out to Lee directly."
        ),
        time_up=(
            "That's all the time we have for this call. Thanks so much for talking with me, "
            "and goodbye!"
        ),
    ),
    "es": Lines(
        blocked="De eso no puedo hablar, pero con gusto te cuento sobre el trabajo de Lee.",
        no_facts=(
            "Hola, soy la versión de IA de Lee. Lo siento, ahora mismo no puedo responder "
            "preguntas porque algo falla de mi lado. Inténtalo más tarde o escríbele a Lee "
            "directamente."
        ),
        time_up=(
            "Se nos acabó el tiempo de esta llamada. Muchas gracias por hablar conmigo, ¡y hasta "
            "luego!"
        ),
    ),
}


def language_rules(start: Language) -> str:
    """The prompt's language section."""
    opening = (
        "The visitor agreed to the terms in Spanish, so the call starts in Spanish."
        if start == "es"
        else "The call starts in English."
    )
    return (
        f"Lee speaks English and fluent Spanish, so you speak either. {opening} "
        "If the visitor asks for Spanish or speaks to you in Spanish, call set_language with es "
        "and answer in Spanish. If they ask for English or speak English, call set_language with "
        "en. Always call set_language before you change language, because it changes your voice. "
        "The facts are written in English. In Spanish, say only what they say, translated "
        "plainly, with nothing added, and keep names of companies, products, programs, "
        "certificates and job titles as written. In Spanish, use gender-neutral wording about "
        "Lee, with no gendered adjectives or pronouns for Lee: say 'Lee tiene experiencia en', "
        "not 'Lee es experto'. "
        "Never speak Portuguese or any other language. If asked, give Lee's level and say the "
        "visitor can hear Lee's real recordings instead."
    )
