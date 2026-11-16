"""Lee's published facts and the prompt section built from them (ADR-19, ADR-21).

The whole published set goes into the prompt, with no retrieval, because a missed lookup is when
the model would improvise (ADR-19). Anything in the prompt can be extracted, so only entries Lee
has published ever get here (ADR-7).

Where facts come from:
- With CLOUD_RUN_URL set, the live published version from cloud-run, fetched at each call start.
  If the fetch fails, the last version this worker fetched is used (ADR-21).
- Without it, the reviewed entries of the local seed file, for development until the seed is
  imported and deleted.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from cloud_run import fetch_published_facts

logger = logging.getLogger("facts")

DEFAULT_FACTS_PATH = Path(__file__).parent / "facts" / "lee.yaml"

# Section keys, in prompt order, with the heading each gets in the prompt.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("profile", "Profile"),
    ("experience", "Experience"),
    ("skills", "Skills"),
    ("spoken_languages", "Spoken languages"),
    ("education", "Education"),
    ("not_skills", "Skills Lee does NOT have (say no plainly)"),
)
STORY_PARTS = ("situation", "task", "action", "result")

GROUNDING_RULES = (
    "Everything you know about Lee is in the facts below, and nothing else is true about Lee. "
    "Answer questions about Lee only from those facts. Each fact has a topic, a level, what is "
    "verified, and limits. Limits are hard rules: never go past them. "
    "Never add numbers, names, dates, tools, results or details that the facts don't state, "
    "even if they seem likely. "
    "If a question isn't covered by the facts, say plainly that you don't have that about Lee "
    "and that the visitor can ask Lee directly. Don't guess, and don't imply Lee knows it. "
    "If a skill is listed under skills Lee does not have, say no plainly. "
    "Don't answer general technical or trivia questions from your own knowledge, even when you "
    "know the answer. Say you're only here to talk about Lee. "
    "Never agree to or discuss offers, pay, start dates or availability; say Lee will follow up "
    "on those. "
    "Never speak Portuguese or any language other than English. If asked, give Lee's level and "
    "say the visitor can hear Lee's real recordings instead."
)

STORY_RULES = (
    "Some facts have stories. When a visitor asks for an example, a time Lee did something, a "
    "challenge Lee faced, a result Lee got, or a STAR answer, pick the one story that fits best "
    "and tell it in order: the situation, the task, the action, then the result. Use one short "
    "spoken sentence for each part, about four sentences in all, and say the result plainly. "
    "Use only that story's own words, numbers and details. Never merge two stories, and never "
    "build a story out of a fact that has none. If no story fits, say Lee hasn't shared a story "
    "for that yet, name the closest story you do have, and offer to tell it. If the visitor "
    "asks for a story about a topic with no story, give that topic's verified facts briefly and "
    "say the visitor can ask Lee for a fuller example."
)


@dataclass(frozen=True)
class Story:
    title: str
    situation: str
    task: str
    action: str
    result: str


@dataclass(frozen=True)
class Fact:
    section: str
    topic: str
    level: str
    verified: str
    limits: str
    stories: tuple[Story, ...] = ()


@dataclass(frozen=True)
class FactSet:
    # Recorded with each call, so Lee knows what the agent knew at the time (ADR-21).
    version: str
    facts: tuple[Fact, ...]


class NoFactsError(RuntimeError):
    """There are no published facts, so the agent can't answer and must end the call."""


def _text(value: object) -> str:
    # YAML folded blocks keep a trailing newline, and empty fields may be None.
    return " ".join(str(value or "").split())


def _fact(section: str, entry: dict) -> Fact:
    return Fact(
        section=section,
        topic=_text(entry.get("topic")),
        level=_text(entry.get("level")),
        verified=_text(entry.get("verified")),
        limits=_text(entry.get("limits")),
        stories=tuple(
            Story(title=_text(s.get("title")), **{p: _text(s.get(p)) for p in STORY_PARTS})
            for s in entry.get("stories") or ()
        ),
    )


def load_facts(path: Path) -> FactSet:
    """Read the local seed file and keep only the entries Lee has reviewed."""
    if not path.is_file():
        raise NoFactsError(f"fact file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    facts = tuple(
        _fact(section, entry)
        for section, _ in SECTIONS
        for entry in data.get(section) or ()
        # `is True`, so a missing or misspelled value counts as a draft and stays out.
        if entry.get("reviewed") is True
    )
    if not facts:
        raise NoFactsError(f"no reviewed facts in {path}")
    return FactSet(version=f"local-{data.get('version', 0)}", facts=facts)


def parse_published(payload: dict) -> FactSet:
    """cloud-run's /internal/facts response. It holds only published entries."""
    known = {section for section, _ in SECTIONS}
    facts = tuple(
        _fact(entry["section"], entry) for entry in payload["facts"] if entry["section"] in known
    )
    if not facts:
        raise NoFactsError("the published version has no facts")
    return FactSet(version=str(payload["version"]), facts=facts)


# The last version this worker fetched, used when cloud-run can't be reached (ADR-21).
_last_fetched: FactSet | None = None


async def get_published_facts() -> FactSet:
    """The facts for this call. The only place that knows where facts come from."""
    global _last_fetched
    base_url = os.getenv("CLOUD_RUN_URL")
    if not base_url:
        return load_facts(Path(os.getenv("FACTS_PATH", DEFAULT_FACTS_PATH)))

    secret = os.environ["AGENT_SIGNING_SECRET"].encode()
    try:
        payload = await fetch_published_facts(base_url, secret)
    # Any failure falls back to the cached version.
    except Exception as error:
        if _last_fetched is None:
            raise NoFactsError("cloud-run unreachable and no cached facts") from error
        # The error type only: the response could hold fact text, and logs stay clean (ADR-14).
        logger.warning(
            "facts fetch failed, using cached version",
            extra={"error": type(error).__name__, "facts_version": _last_fetched.version},
        )
        return _last_fetched
    if payload is None:
        # Nothing published is a real answer, not an outage, so the cache isn't used.
        raise NoFactsError("nothing published")
    _last_fetched = parse_published(payload)
    return _last_fetched


def facts_prompt(fact_set: FactSet) -> str:
    """The facts as a prompt section, grouped under their section headings."""
    lines = ["FACTS ABOUT LEE"]
    for section, heading in SECTIONS:
        entries = [fact for fact in fact_set.facts if fact.section == section]
        if not entries:
            continue
        lines.append(f"\n## {heading}")
        for fact in entries:
            lines.append(f"- Topic: {fact.topic}")
            if fact.level:
                lines.append(f"  Level: {fact.level}")
            if fact.verified:
                lines.append(f"  Verified: {fact.verified}")
            if fact.limits:
                lines.append(f"  Limits: {fact.limits}")
            for story in fact.stories:
                lines.append(f"  Story: {story.title}")
                for part in STORY_PARTS:
                    if text := getattr(story, part):
                        lines.append(f"    {part.capitalize()}: {text}")
    return "\n".join(lines)
