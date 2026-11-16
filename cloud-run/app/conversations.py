"""Transcripts, call endings, summaries, and the admin's view of conversations (ADR-6, ADR-9).

Firestore layout, all under the session's `delete_at` (ADR-6, I10):
- `sessions/{id}`: consent, then `status` (created, active, ended), `started_at`, `ended_at`,
  `end_reason`, `facts_version`, and the summary fields once the call ends.
- `sessions/{id}/transcript/{batch}`: one document per batch the agent sends, holding its turns.
- `contacts/{id}`: the optional form, kept apart from the transcript (ADR-8).

A batch number is used once. Resending it, including a replay of a signed request inside its
time window, writes nothing and gets `Duplicate` (ADR-9).
"""

import logging
from datetime import UTC, datetime
from typing import Literal

from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

from app import summary
from app.config import Settings
from app.notify import notify_admin

logger = logging.getLogger(__name__)

ROOM_PREFIX = "session-"
MAX_CONVERSATIONS = 100


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker: Literal["visitor", "agent"]
    text: str = Field(min_length=1, max_length=4000)
    # Set by the agent on a turn it counted as inappropriate, so Lee sees why a call ended (I8).
    violation: bool = False


class TranscriptBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch: int = Field(ge=0, le=100_000)
    turns: list[Turn] = Field(max_length=200)
    # The published facts version the agent used for this call (ADR-21).
    facts_version: int | None = Field(default=None, ge=1)
    # The agent's last batch. The call is ended and summarized after it's written.
    final: bool = False


class NoSession(Exception):
    pass


class SessionEnded(Exception):
    pass


class Duplicate(Exception):
    pass


def _session(db: firestore.Client, session_id: str):
    return db.collection("sessions").document(session_id)


def _batch_id(number: int) -> str:
    # Zero-padded, so document IDs sort by number.
    return f"{number:06d}"


@firestore.transactional
def _add_batch(transaction, db: firestore.Client, session_id: str, batch: TranscriptBatch):
    session_ref = _session(db, session_id)
    batch_ref = session_ref.collection("transcript").document(_batch_id(batch.batch))
    session = session_ref.get(transaction=transaction)
    existing = batch_ref.get(transaction=transaction)
    if not session.exists:
        raise NoSession
    data = session.to_dict()
    if existing.exists:
        raise Duplicate
    if data["status"] == "ended":
        raise SessionEnded

    now = datetime.now(UTC)
    transaction.set(
        batch_ref,
        {
            "turns": [turn.model_dump() for turn in batch.turns],
            "received_at": now,
            "delete_at": data["delete_at"],
        },
    )
    update = {"status": "active", "last_batch_at": now}
    if "started_at" not in data:
        update["started_at"] = now
    if batch.facts_version is not None:
        update["facts_version"] = batch.facts_version
    transaction.update(session_ref, update)


def add_batch(db: firestore.Client, session_id: str, batch: TranscriptBatch) -> None:
    """Raises NoSession, Duplicate or SessionEnded, and writes nothing in each case."""
    _add_batch(db.transaction(), db, session_id, batch)


@firestore.transactional
def _claim_end(transaction, session_ref, reason: str) -> bool:
    session = session_ref.get(transaction=transaction)
    if not session.exists or session.to_dict()["status"] == "ended":
        return False
    transaction.update(
        session_ref,
        {"status": "ended", "ended_at": datetime.now(UTC), "end_reason": reason},
    )
    return True


def turns(db: firestore.Client, session_id: str) -> list[dict]:
    batches = _session(db, session_id).collection("transcript").order_by("__name__").stream()
    return [turn for batch in batches for turn in batch.to_dict()["turns"]]


def end_session(db: firestore.Client, settings: Settings, session_id: str, reason: str) -> bool:
    """Ends the call once, then writes its summary and emails the admin a link.

    The agent's final batch and the `room_finished` webhook can both arrive. Only the first one
    to claim the session summarizes it; the other returns False and changes nothing.
    """
    session_ref = _session(db, session_id)
    if not _claim_end(db.transaction(), session_ref, reason):
        return False

    transcript = turns(db, session_id)
    if not transcript:
        result = {"summary": "", "declined_questions": [], "summary_status": "empty"}
    else:
        try:
            written = summary.generate(transcript)
            result = {**written.model_dump(), "summary_status": "done"}
        except Exception as error:  # noqa: BLE001 - any model failure leaves the call saved
            # The type only. The message could quote the transcript (ADR-14).
            logger.warning("Summary failed: %s", type(error).__name__)
            result = {"summary": "", "declined_questions": [], "summary_status": "failed"}
    session_ref.update(result)
    notify_admin(settings)
    return True


def session_id_from_room(room: str) -> str | None:
    if not room.startswith(ROOM_PREFIX):
        return None
    session_id = room.removeprefix(ROOM_PREFIX)
    # Session IDs are token_urlsafe(16). Anything else didn't come from this service.
    if not session_id or len(session_id) > 64 or "/" in session_id:
        return None
    return session_id


def _seconds(start: datetime | None, end: datetime | None) -> int:
    return int((end - start).total_seconds()) if start and end else 0


def list_conversations(db: firestore.Client) -> list[dict]:
    """Newest first, with each session's invite label, contact details and transcript (A6)."""
    sessions = list(
        db.collection("sessions")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(MAX_CONVERSATIONS)
        .stream()
    )
    if not sessions:
        return []
    invite_ids = {s.get("invite_id") for s in sessions}
    invites = {
        snap.id: snap.to_dict()
        for snap in db.get_all([db.collection("invites").document(i) for i in invite_ids])
        if snap.exists
    }
    contacts = {
        snap.id: snap.to_dict()
        for snap in db.get_all([db.collection("contacts").document(s.id) for s in sessions])
        if snap.exists
    }

    conversations = []
    for snap in sessions:
        data = snap.to_dict()
        contact = contacts.get(snap.id)
        conversations.append(
            {
                "id": snap.id,
                "inviteLabel": invites.get(data["invite_id"], {}).get("label", ""),
                "startedAt": data.get("started_at", data["created_at"]).isoformat(),
                "durationSeconds": _seconds(data.get("started_at"), data.get("ended_at")),
                "status": data["status"],
                "factsVersion": data.get("facts_version"),
                "summary": data.get("summary", ""),
                "summaryStatus": data.get("summary_status"),
                "declinedQuestions": data.get("declined_questions", []),
                "transcript": [
                    {k: t[k] for k in ("speaker", "text", "violation")} for t in turns(db, snap.id)
                ],
                **(
                    {
                        "contact": {
                            k: contact[k] for k in ("name", "email", "company") if k in contact
                        }
                    }
                    if contact
                    else {}
                ),
            }
        )
    return conversations


def delete_conversation(db: firestore.Client, session_id: str) -> None:
    """Deletes the session, its transcript and summary, and its contact details (A7).

    The invite stays, because other sessions can point to it. Its label is removed by TTL.
    """
    session_ref = _session(db, session_id)
    db.recursive_delete(session_ref)
    session_ref.delete()
    db.collection("contacts").document(session_id).delete()
