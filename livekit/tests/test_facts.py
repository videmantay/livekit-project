import os
from pathlib import Path

import pytest
import yaml

import facts
from config import DEFAULT_FACTS_PATH
from facts import NoFactsError, facts_prompt, load_facts

FIXTURE = """
version: 3
skills:
  - topic: Published skill
    level: Professional
    verified: Did the thing.
    limits: Don't expand.
    reviewed: true
  - topic: Draft skill
    level: Professional
    verified: Not approved yet.
    limits: ""
    reviewed: false
  - topic: Missing review flag
    verified: Should stay out.
not_skills:
  - topic: Pen testing
    level: None
    verified: ""
    limits: Not a security specialist.
    reviewed: true
"""


@pytest.fixture
def fixture_path(tmp_path: Path) -> Path:
    path = tmp_path / "facts.yaml"
    path.write_text(FIXTURE, encoding="utf-8")
    return path


def test_drafts_never_reach_the_prompt(fixture_path: Path) -> None:
    # Anything in the prompt can be extracted, so only reviewed entries go in (ADR-7).
    prompt = facts_prompt(load_facts(fixture_path))
    assert "Published skill" in prompt
    assert "Draft skill" not in prompt
    assert "Not approved yet" not in prompt
    assert "Missing review flag" not in prompt


def test_not_skills_are_under_their_own_heading(fixture_path: Path) -> None:
    prompt = facts_prompt(load_facts(fixture_path))
    heading = prompt.index("Lee does NOT have")
    assert prompt.index("Pen testing") > heading
    assert prompt.index("Published skill") < heading


def test_version_is_recorded(fixture_path: Path) -> None:
    assert load_facts(fixture_path).version == "local-3"


def test_no_reviewed_facts_means_no_calls(tmp_path: Path) -> None:
    path = tmp_path / "facts.yaml"
    path.write_text("skills:\n  - topic: x\n    reviewed: false\n", encoding="utf-8")
    with pytest.raises(NoFactsError):
        load_facts(path)


def test_missing_file_means_no_calls(tmp_path: Path) -> None:
    with pytest.raises(NoFactsError):
        load_facts(tmp_path / "absent.yaml")


def test_every_reviewed_topic_in_the_real_file_is_in_the_prompt() -> None:
    data = yaml.safe_load(DEFAULT_FACTS_PATH.read_text(encoding="utf-8"))
    reviewed = [
        " ".join(entry["topic"].split())
        for value in data.values()
        if isinstance(value, list)
        for entry in value
        if isinstance(entry, dict) and entry.get("reviewed") is True
    ]
    prompt = facts_prompt(load_facts(DEFAULT_FACTS_PATH))
    assert reviewed
    for topic in reviewed:
        assert topic in prompt


def test_prompt_never_contains_the_legal_name() -> None:
    # The legal name comes from config, never code (ADR-14), so the test reads it from the env.
    legal_name = os.getenv("LEE_LEGAL_NAME")
    if not legal_name:
        pytest.skip("set LEE_LEGAL_NAME to run this check")
    prompt = facts_prompt(load_facts(DEFAULT_FACTS_PATH)).lower()
    for part in legal_name.lower().split():
        if part != "lee":
            assert part not in prompt


STORY_FIXTURE = """
experience:
  - topic: Example job
    verified: Did things.
    reviewed: true
    stories:
      - title: The migration
        situation: Old system was failing.
        task: Move it without downtime.
        action: Ran both side by side.
        result: Cut over with zero downtime.
"""


def test_stories_render_in_star_order(tmp_path: Path) -> None:
    path = tmp_path / "facts.yaml"
    path.write_text(STORY_FIXTURE, encoding="utf-8")
    prompt = facts_prompt(load_facts(path))
    parts = ["Story: The migration", "Situation:", "Task:", "Action:", "Result: Cut over"]
    positions = [prompt.index(part) for part in parts]
    assert positions == sorted(positions)


PUBLISHED = {
    "version": 7,
    "facts": [
        {
            "section": "skills",
            "topic": "Python",
            "level": "Daily",
            "verified": "Pipelines.",
            "limits": "",
            "stories": [],
        },
        {"section": "unknown", "topic": "Ignored", "level": "", "verified": "", "limits": ""},
    ],
}


def test_published_payload_is_parsed() -> None:
    fact_set = facts.parse_published(PUBLISHED)
    assert fact_set.version == "7"
    assert [f.topic for f in fact_set.facts] == ["Python"]


@pytest.fixture
def from_cloud_run(monkeypatch: pytest.MonkeyPatch) -> list:
    monkeypatch.setenv("CLOUD_RUN_URL", "https://cloud-run.example")
    monkeypatch.setenv("AGENT_SIGNING_SECRET", "x" * 32)
    monkeypatch.setattr(facts, "_last_fetched", None)
    responses: list = []

    async def fetch(base_url: str, secret: bytes):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(facts, "fetch_published_facts", fetch)
    return responses


@pytest.mark.asyncio
async def test_fetch_failure_uses_the_last_version(from_cloud_run: list) -> None:
    from_cloud_run.extend([PUBLISHED, OSError("down")])
    assert (await facts.get_published_facts()).version == "7"
    assert (await facts.get_published_facts()).version == "7"


@pytest.mark.asyncio
async def test_fetch_failure_with_nothing_cached_ends_the_call(from_cloud_run: list) -> None:
    from_cloud_run.append(OSError("down"))
    with pytest.raises(NoFactsError):
        await facts.get_published_facts()


@pytest.mark.asyncio
async def test_nothing_published_ends_the_call_even_with_a_cache(from_cloud_run: list) -> None:
    from_cloud_run.extend([PUBLISHED, None])
    await facts.get_published_facts()
    with pytest.raises(NoFactsError):
        await facts.get_published_facts()
