import json

import aiohttp
import pytest

import transcript as transcript_module
from cloud_run import signature
from transcript import (
    BATCH_TURNS,
    FINAL_TIMEOUT_SECONDS,
    Transcript,
    cloud_run_post,
    facts_version_number,
    session_id_from_metadata,
)

# Exchanges (a visitor turn and an agent turn) that fill exactly one mid-call batch.
ONE_BATCH = BATCH_TURNS // 2


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(transcript_module, "RETRY_DELAY_SECONDS", 0)


class FakeCloudRun:
    """Stores batches like cloud-run: a number once, nothing after the final one."""

    def __init__(self, statuses: list[int | Exception] | None = None) -> None:
        self.statuses = list(statuses or [])
        self.requests: list[tuple[dict, float]] = []
        self.stored: dict[int, dict] = {}

    async def post(self, batch: dict, timeout: float) -> int:
        self.requests.append((batch, timeout))
        if self.statuses:
            status = self.statuses.pop(0)
            if isinstance(status, Exception):
                raise status
            if status != 201:
                return status
        if batch["batch"] in self.stored or any(b["final"] for b in self.stored.values()):
            return 409
        self.stored[batch["batch"]] = batch
        return 201

    def turns(self) -> list[dict]:
        return [turn for number in sorted(self.stored) for turn in self.stored[number]["turns"]]


def conversation(transcript: Transcript, exchanges: int) -> None:
    for i in range(exchanges):
        transcript.add(f"user_{i}", "user", f"question {i}")
        transcript.add(f"agent_{i}", "assistant", f"answer {i}")


async def wait_for_sends(transcript: Transcript) -> None:
    for task in list(transcript._tasks):
        await task


@pytest.mark.asyncio
async def test_final_batch_carries_every_turn_in_order() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post, facts_version=3)
    conversation(transcript, 5)
    await transcript.finish()

    assert [t["text"] for t in cloud_run.turns()] == [
        text for i in range(5) for text in (f"question {i}", f"answer {i}")
    ]
    numbers = sorted(cloud_run.stored)
    assert numbers == list(range(len(numbers)))
    assert [cloud_run.stored[n]["final"] for n in numbers] == [False] * (len(numbers) - 1) + [True]
    assert all(b["facts_version"] == 3 for b in cloud_run.stored.values())


@pytest.mark.asyncio
async def test_sends_batches_during_the_call() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, BATCH_TURNS)
    await wait_for_sends(transcript)
    assert cloud_run.stored, "a batch should go before the call ends"
    assert not any(b["final"] for b in cloud_run.stored.values())


@pytest.mark.asyncio
async def test_final_request_gets_the_longer_timeout() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, 1)
    await transcript.finish()
    batch, timeout = cloud_run.requests[-1]
    assert batch["final"] and timeout == FINAL_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_agent_tags_are_stripped_and_empty_turns_dropped() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    transcript.add("a", "assistant", "[laughs] Sure, happy to help.")
    transcript.add("b", "assistant", "[sighs]")
    transcript.add("c", "user", "   ")
    transcript.add("d", "system", "instructions")
    await transcript.finish()
    assert cloud_run.turns() == [
        {"speaker": "agent", "text": "Sure, happy to help.", "violation": False}
    ]


@pytest.mark.asyncio
async def test_blocked_visitor_turns_are_marked() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post, is_violation=lambda mid: mid == "user_1")
    conversation(transcript, 2)
    await transcript.finish()
    assert [t["violation"] for t in cloud_run.turns()] == [False, False, True, False]


@pytest.mark.asyncio
async def test_empty_call_still_sends_final() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    await transcript.finish()
    assert cloud_run.stored == {0: {"batch": 0, "turns": [], "final": True}}


@pytest.mark.asyncio
async def test_finish_twice_sends_once() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    await transcript.finish()
    await transcript.finish()
    assert len(cloud_run.requests) == 1


@pytest.mark.asyncio
async def test_retry_after_lost_response_counts_409_as_stored() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, 1)

    real_post = cloud_run.post

    async def lose_first_response(batch: dict, timeout: float) -> int:
        status = await real_post(batch, timeout)
        if len(cloud_run.requests) == 1:
            raise TimeoutError  # stored, but the agent never heard back
        return status

    transcript.post = lose_first_response
    await transcript.finish()
    assert [b["batch"] for b, _ in cloud_run.requests] == [0, 0]
    assert len(cloud_run.turns()) == 2


@pytest.mark.asyncio
async def test_failed_batch_is_resent_unchanged_later() -> None:
    # cloud-run is down for the first mid-call batch, then comes back.
    cloud_run = FakeCloudRun(statuses=[503, 503, 503])
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, ONE_BATCH)
    await wait_for_sends(transcript)
    assert not cloud_run.stored
    first = cloud_run.requests[0][0]

    conversation(transcript, 1)
    await transcript.finish()
    assert cloud_run.stored[0] == first
    assert len(cloud_run.turns()) == BATCH_TURNS + 2


@pytest.mark.asyncio
async def test_final_is_sent_even_when_an_earlier_batch_fails() -> None:
    cloud_run = FakeCloudRun(statuses=[aiohttp.ClientError()] * 3)
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, ONE_BATCH)
    await wait_for_sends(transcript)
    cloud_run.statuses = [aiohttp.ClientError()] * 3  # the queued batch fails again
    await transcript.finish()
    assert any(b["final"] for b in cloud_run.stored.values())


@pytest.mark.asyncio
async def test_unknown_session_stops_sending() -> None:
    cloud_run = FakeCloudRun(statuses=[404])
    transcript = Transcript(post=cloud_run.post)
    conversation(transcript, BATCH_TURNS * 2)
    await wait_for_sends(transcript)
    await transcript.finish()
    assert len(cloud_run.requests) == 1


@pytest.mark.asyncio
async def test_long_call_splits_into_batches_cloud_run_accepts() -> None:
    cloud_run = FakeCloudRun()
    transcript = Transcript(post=cloud_run.post)
    for i in range(250):
        transcript.add(f"u{i}", "user", "x" * 5000)
    await transcript.finish()
    assert all(len(b["turns"]) <= 200 for b in cloud_run.stored.values())
    assert all(len(t["text"]) == 4000 for t in cloud_run.turns())
    assert len(cloud_run.turns()) == 250


def test_facts_version_only_sends_cloud_run_versions() -> None:
    assert facts_version_number("7") == 7
    assert facts_version_number("local-3") is None
    assert facts_version_number("0") is None
    assert facts_version_number(None) is None


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"session_id": "abc_DEF-123"}, "abc_DEF-123"),
        ({}, None),
        ({"session_id": 5}, None),
        ({"session_id": "../facts"}, None),
        ({"session_id": "x" * 65}, None),
    ],
)
def test_session_id_from_metadata(metadata: dict, expected: str | None) -> None:
    assert session_id_from_metadata(metadata) == expected


def test_no_sender_without_cloud_run() -> None:
    assert cloud_run_post("abc") is None


@pytest.mark.asyncio
async def test_post_signs_the_exact_body(monkeypatch) -> None:
    secret = "s" * 32
    monkeypatch.setenv("CLOUD_RUN_URL", "https://cloud-run.example/")
    monkeypatch.setenv("AGENT_SIGNING_SECRET", secret)
    sent = {}

    class FakeResponse:
        status = 201

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

    class FakeSession:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, data, headers):
            sent.update(url=url, data=data, headers=headers)
            return FakeResponse()

    monkeypatch.setattr(aiohttp, "ClientSession", FakeSession)
    post = cloud_run_post("abc")
    assert await post({"batch": 0, "turns": [], "final": True}, 5) == 201

    path = "/internal/sessions/abc/transcript"
    assert sent["url"] == "https://cloud-run.example" + path
    assert json.loads(sent["data"]) == {"batch": 0, "turns": [], "final": True}
    headers = sent["headers"]
    assert headers["X-Agent-Signature"] == signature(
        secret.encode(), headers["X-Agent-Timestamp"], "POST", path, sent["data"]
    )
