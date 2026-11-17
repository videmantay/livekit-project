"""Keeps the twin from standing silent while the model is slow (I7).

A voice call can't go quiet: after a couple of seconds the visitor thinks it's broken. So if
the model hasn't produced any words yet, a short line is spoken while it works, and after a
hard limit the reply is given up on, so the agent can apologize instead of hanging.

The lines are holding phrases, never part of an answer. They can't promise one, because the
reply that follows is often a plain "Lee hasn't shared that" (ADR-19).
"""

import asyncio
import random
from collections.abc import AsyncIterable, AsyncIterator, Sequence

from livekit.agents import llm


class ReplyTimeout(TimeoutError):
    """The model produced no words before the limit."""


class HoldingLine(str):
    """A line `paced` added, so callers can tell it from the model's own words."""


def has_words(chunk: llm.ChatChunk | str) -> bool:
    if isinstance(chunk, str):
        return bool(chunk.strip())
    return bool(chunk.delta and chunk.delta.content and chunk.delta.content.strip())


async def paced(
    stream: AsyncIterable[llm.ChatChunk | str],
    stages: Sequence[tuple[float, Sequence[str]]],
    give_up_after: float,
) -> AsyncIterator[llm.ChatChunk | str]:
    """The stream's chunks, with a holding line spoken at each stage the first words miss.

    `stages` are (seconds since the start, lines to pick one from), in order. Raises
    ReplyTimeout if no words have come by `give_up_after`. Once words arrive, nothing is added
    and there's no limit, so a long answer is never cut off.
    """
    loop = asyncio.get_running_loop()
    start = loop.time()
    pending = list(stages)
    speaking = False
    iterator = aiter(stream)
    step: asyncio.Future | None = None
    try:
        while True:
            step = asyncio.ensure_future(anext(iterator))
            while not speaking and not step.done():
                deadline = pending[0][0] if pending else give_up_after
                remaining = start + min(deadline, give_up_after) - loop.time()
                await asyncio.wait({step}, timeout=max(remaining, 0))
                if step.done():
                    break
                if not pending or pending[0][0] >= give_up_after:
                    raise ReplyTimeout
                _, lines = pending.pop(0)
                # Trailing space, so the answer that follows starts as a new sentence.
                yield HoldingLine(random.choice(lines).rstrip() + " ")
            try:
                chunk = await step
            except StopAsyncIteration:
                return
            step = None
            if has_words(chunk):
                speaking = True
            yield chunk
    finally:
        # Stops the model request too: the stream is closed, not left running.
        if step is not None and not step.done():
            step.cancel()
            await asyncio.gather(step, return_exceptions=True)
        if hasattr(iterator, "aclose"):
            await iterator.aclose()
