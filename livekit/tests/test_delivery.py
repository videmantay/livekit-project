from collections.abc import AsyncIterable

import pytest
from livekit.agents.voice.io import TimedString

from delivery import (
    ALLOWED_TAGS,
    DELIVERY_NOTES,
    TagFilter,
    allow_listed_tags_only,
    strip_tags,
    without_tags,
)


async def _stream(*chunks: str) -> AsyncIterable[str]:
    for chunk in chunks:
        yield chunk


async def _collect(stream: AsyncIterable[str]) -> list[str]:
    return [chunk async for chunk in stream]


@pytest.mark.parametrize("tag", sorted(ALLOWED_TAGS))
def test_prompt_lists_every_allowed_tag(tag: str) -> None:
    assert f"[{tag}]" in DELIVERY_NOTES


@pytest.mark.asyncio
async def test_tts_keeps_allowed_tags_split_across_chunks() -> None:
    out = await _collect(
        allow_listed_tags_only(_stream("Oh [la", "ughs] yeah, ", "so..."))
    )
    assert "".join(out) == "Oh [laughs] yeah, so..."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tag", ["[fart]", "[applause]", "[strong French accent]", "[sings]"]
)
async def test_tts_drops_tags_not_on_the_allowlist(tag: str) -> None:
    # A visitor can't make Lee's voice do sound effects or accents by asking.
    out = await _collect(allow_listed_tags_only(_stream(f"Sure {tag} here you go.")))
    assert "".join(out) == "Sure here you go."


def test_allowlist_ignores_case_and_padding() -> None:
    tag_filter = TagFilter(keep=ALLOWED_TAGS)
    assert tag_filter.feed("[ Laughs ] ok") == "[ Laughs ] ok"


def test_long_bracket_is_plain_text_not_a_held_tag() -> None:
    text = "[" + "x" * 40 + "] done"
    assert strip_tags(text) == text


def test_unclosed_bracket_is_kept_at_end_of_reply() -> None:
    assert strip_tags("see [note") == "see [note"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Oh [laughs] yeah.", "Oh yeah."),
        ("[warmly] Hi there.", "Hi there."),
        ("Honestly... [sighs]", "Honestly... "),
        ("No tags here.", "No tags here."),
    ],
)
def test_strip_tags_leaves_clean_text(text: str, expected: str) -> None:
    assert strip_tags(text) == expected


@pytest.mark.asyncio
async def test_captions_drop_tags_and_keep_word_timing() -> None:
    async def words() -> AsyncIterable[str | TimedString]:
        yield TimedString("Oh ", start_time=0.0, end_time=0.2)
        yield TimedString("[laughs] ", start_time=0.2, end_time=0.9)
        yield TimedString("yeah", start_time=0.9, end_time=1.1)

    out = await _collect(without_tags(words()))
    assert "".join(out) == "Oh yeah"
    assert isinstance(out[-1], TimedString)
    assert out[-1].start_time == 0.9
