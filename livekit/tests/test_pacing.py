import asyncio

import pytest
from livekit.agents import llm

from pacing import HoldingLine, ReplyTimeout, has_words, paced

# Short times, so the tests run fast. The real ones are in agent.py.
STAGES = ((0.05, ("thinking",)), (0.15, ("still thinking",)))
LIMIT = 0.3


def chunk(text: str | None) -> llm.ChatChunk:
    return llm.ChatChunk(id="c", delta=llm.ChoiceDelta(role="assistant", content=text))


async def model(first_after: float, texts: list[str | None], gap: float = 0.0):
    await asyncio.sleep(first_after)
    for text in texts:
        yield chunk(text)
        await asyncio.sleep(gap)


async def collect(stream) -> list[str]:
    return [c if isinstance(c, str) else c.delta.content for c in [x async for x in stream]]


@pytest.mark.asyncio
async def test_fast_reply_gets_no_holding_line() -> None:
    out = await collect(paced(model(0, ["Sure.", " Lee did that."]), STAGES, LIMIT))
    assert out == ["Sure.", " Lee did that."]


@pytest.mark.asyncio
async def test_slow_reply_gets_one_holding_line_first() -> None:
    out = [x async for x in paced(model(0.1, ["Sure."]), STAGES, LIMIT)]
    assert out[0] == "thinking " and isinstance(out[0], HoldingLine)
    assert not isinstance(out[1], HoldingLine) and out[1].delta.content == "Sure."


@pytest.mark.asyncio
async def test_slower_reply_gets_both_lines_in_order() -> None:
    out = await collect(paced(model(0.2, ["Sure."]), STAGES, LIMIT))
    assert out == ["thinking ", "still thinking ", "Sure."]


@pytest.mark.asyncio
async def test_gives_up_when_no_words_by_the_limit() -> None:
    with pytest.raises(ReplyTimeout):
        await collect(paced(model(5, ["too late"]), STAGES, LIMIT))


@pytest.mark.asyncio
async def test_chunks_without_words_dont_count_as_speaking() -> None:
    # Gemini can send empty chunks (thinking, usage) before any words.
    out = await collect(paced(model(0, [None, "", None], gap=0.08), STAGES, LIMIT))
    assert "thinking " in out


@pytest.mark.asyncio
async def test_long_answer_is_never_cut_off() -> None:
    texts = [f"word{i} " for i in range(8)]
    out = await collect(paced(model(0, texts, gap=0.06), STAGES, LIMIT))
    assert out == texts


@pytest.mark.asyncio
async def test_model_errors_pass_through() -> None:
    async def failing():
        await asyncio.sleep(0.01)
        raise RuntimeError("boom")
        yield  # pragma: no cover

    with pytest.raises(RuntimeError):
        await collect(paced(failing(), STAGES, LIMIT))


@pytest.mark.asyncio
async def test_giving_up_closes_the_model_stream() -> None:
    closed = asyncio.Event()

    async def hanging():
        try:
            await asyncio.sleep(5)
            yield chunk("never")
        finally:
            closed.set()

    with pytest.raises(ReplyTimeout):
        await collect(paced(hanging(), STAGES, LIMIT))
    assert closed.is_set()


def test_has_words() -> None:
    assert has_words("hi")
    assert not has_words("  ")
    assert has_words(chunk("hi"))
    assert not has_words(chunk(None))

