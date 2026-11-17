"""The call transcript, sent in numbered batches to cloud-run's signed endpoint (A4, ADR-2, ADR-9).

Turns are collected from the session's chat history as they're committed, then sent in batches
during the call, so a crash loses only the last few. The last batch has `final: true`. cloud-run
then ends the call and writes the summary, so that request waits for Gemini and gets a longer
timeout.

A batch's number and turns are fixed once it's made. A batch that can't be sent stays queued
and is resent as is, so a retry of a request that did arrive gets 409 and nothing is stored
twice. That's why a 409 counts as stored.

Agent turns go through `strip_tags`, because chat history keeps audio tags such as [laughs].
Logs hold batch numbers, counts and statuses only, never turn text (ADR-14).
"""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import aiohttp

from cloud_run import post_transcript_batch
from config import CloudRunSettings
from delivery import strip_tags

logger = logging.getLogger("transcript")

# A batch is sent once this many turns are waiting, and only after an agent turn, so a
# visitor turn's violation flag is known before it's sent.
BATCH_TURNS = 6
# cloud-run's limits on a batch and a turn (cloud-run/app/conversations.py).
MAX_BATCH_TURNS = 200
MAX_TURN_CHARS = 4000
# Matches cloud-run's SessionId path pattern.
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

BATCH_TIMEOUT_SECONDS = 10.0
# The final request waits for the summary, which Gemini writes before cloud-run answers.
FINAL_TIMEOUT_SECONDS = 90.0
ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0

# (batch, timeout) -> HTTP status. Raises on network errors.
Post = Callable[[dict, float], Awaitable[int]]


@dataclass
class _Turn:
    message_id: str
    speaker: str
    text: str


@dataclass
class _Batch:
    number: int
    turns: list[dict]
    final: bool = False


def facts_version_number(version: str | None) -> int | None:
    """cloud-run versions are whole numbers. The local seed's "local-N" isn't sent."""
    if version and version.isdigit() and int(version) >= 1:
        return int(version)
    return None


@dataclass
class Transcript:
    post: Post
    facts_version: int | None = None
    # Visitor messages counted as violations, such as the ones Gemini blocked (I8).
    is_violation: Callable[[str], bool] = lambda _message_id: False

    _waiting: list[_Turn] = field(default_factory=list)
    _outbox: list[_Batch] = field(default_factory=list)
    _next_number: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _tasks: set[asyncio.Task] = field(default_factory=set)
    _finished: bool = False
    # Set when cloud-run has no such session, so nothing more is sent.
    _gone: bool = False

    def add(self, message_id: str, role: str, text: str | None) -> None:
        """One message committed to chat history. Only visitor and agent text is kept."""
        if self._finished or role not in ("user", "assistant") or not text:
            return
        if role == "assistant":
            text = strip_tags(text)
        text = text.strip()[:MAX_TURN_CHARS]
        if not text:
            return
        speaker = "visitor" if role == "user" else "agent"
        self._waiting.append(_Turn(message_id, speaker, text))
        if speaker == "agent" and len(self._waiting) >= BATCH_TURNS:
            self._pack()
            task = asyncio.create_task(self._send_outbox())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def finish(self) -> None:
        """Sends everything left with `final: true` last. Safe to call more than once."""
        if self._finished:
            return
        self._finished = True
        self._pack(final=True)
        await self._send_outbox(final=True)

    def _pack(self, final: bool = False) -> None:
        turns = [
            {
                "speaker": turn.speaker,
                "text": turn.text,
                "violation": turn.speaker == "visitor" and self.is_violation(turn.message_id),
            }
            for turn in self._waiting
        ]
        self._waiting = []
        # A final batch is made even with no turns, so cloud-run always hears the call ended.
        chunks = [turns[i : i + MAX_BATCH_TURNS] for i in range(0, len(turns), MAX_BATCH_TURNS)]
        if final and not chunks:
            chunks = [[]]
        for index, chunk in enumerate(chunks):
            last = index == len(chunks) - 1
            self._outbox.append(_Batch(self._next_number, chunk, final=final and last))
            self._next_number += 1

    async def _send_outbox(self, final: bool = False) -> None:
        # One sender at a time, so batches arrive in order.
        async with self._lock:
            while self._outbox and not self._gone:
                batch = self._outbox[0]
                if await self._send(batch) or final:
                    # At the end of a call nothing comes later, so a batch that failed is
                    # dropped and the final one is still sent.
                    self._outbox.pop(0)
                else:
                    # Kept for the next send, unchanged.
                    return

    async def _send(self, batch: _Batch) -> bool:
        """True once cloud-run has the batch, or it never can. False to try again later."""
        body = {"batch": batch.number, "turns": batch.turns, "final": batch.final}
        if self.facts_version is not None:
            body["facts_version"] = self.facts_version
        timeout = FINAL_TIMEOUT_SECONDS if batch.final else BATCH_TIMEOUT_SECONDS
        log = {"batch": batch.number, "turns": len(batch.turns), "final": batch.final}
        for attempt in range(ATTEMPTS):
            if attempt:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)
            try:
                status = await self.post(body, timeout)
            except (aiohttp.ClientError, TimeoutError) as error:
                logger.warning("transcript send failed", extra={**log, "error": type(error).__name__})
                continue
            if status == 201:
                logger.info("transcript batch stored", extra=log)
                return True
            if status == 409:
                # Already stored by an earlier attempt, or the call has already ended.
                logger.info("transcript batch refused as stored or ended", extra=log)
                return True
            if status == 404:
                logger.error("transcript session not found, sending stopped", extra=log)
                self._gone = True
                return True
            if 400 <= status < 500:
                # A request cloud-run will never accept. Retrying can't help.
                logger.error("transcript batch rejected", extra={**log, "status": status})
                return True
            logger.warning("transcript send failed", extra={**log, "status": status})
        return False


def session_id_from_metadata(metadata: dict) -> str | None:
    value = metadata.get("session_id")
    return value if isinstance(value, str) and SESSION_ID.match(value) else None


def cloud_run_post(session_id: str) -> Post | None:
    """The sender for this call's session, or None when cloud-run isn't configured."""
    settings = CloudRunSettings()
    if not settings.cloud_run_url:
        return None
    secret = settings.agent_signing_secret.get_secret_value().encode()

    async def post(batch: dict, timeout: float) -> int:
        return await post_transcript_batch(
            settings.cloud_run_url, secret, session_id, batch, timeout
        )

    return post
