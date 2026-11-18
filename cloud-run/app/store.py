import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from google.api_core.exceptions import Aborted
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import get_settings


class InviteBusy(Exception):
    """Every transaction attempt hit contention. Nothing was written, so no session was used."""


class LineBusy(Exception):
    """The most calls allowed at once are live. Nothing was written, so no session was used."""


class NoSuchSession(Exception):
    pass


# A session counts as live until it ends, or until it's older than the longest call plus this.
# The grace covers a call whose end never arrived: a visitor who never joined the room gets no
# room_finished webhook, and a dead agent sends no final batch.
LIVE_CALL_GRACE = timedelta(minutes=2)


def _live_calls(transaction, db: firestore.Client, now: datetime, max_session_minutes: int) -> int:
    cutoff = now - timedelta(minutes=max_session_minutes) - LIVE_CALL_GRACE
    # One range filter on one field, so the default single-field index covers it.
    recent = db.collection("sessions").where(filter=FieldFilter("created_at", ">=", cutoff))
    return sum(1 for s in transaction.get(recent) if s.to_dict().get("status") != "ended")


@lru_cache
def get_db() -> firestore.Client:
    return firestore.Client(project=get_settings().firebase_project_id)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_invite(
    db: firestore.Client, label: str, max_sessions: int, expires_at: datetime, retention_days: int
) -> tuple[str, str]:
    """Returns (code, invite_id). The code is never stored, so it can't be shown again.

    The label can name a person, so the invite gets a `delete_at` (ADR-6). It counts from
    expiry, because a session started just before expiry is kept for `retention_days`, and the
    invite has to outlive the sessions that point to it.
    """
    code = secrets.token_urlsafe(18)
    invite_id = hash_code(code)
    db.collection("invites").document(invite_id).set(
        {
            "label": label,
            "max_sessions": max_sessions,
            "sessions_used": 0,
            "expires_at": expires_at,
            "revoked": False,
            "created_at": datetime.now(UTC),
            "delete_at": expires_at + timedelta(days=retention_days),
        }
    )
    return code, invite_id


def _is_usable(invite: dict | None) -> bool:
    if invite is None or invite["revoked"]:
        return False
    if invite["expires_at"] <= datetime.now(UTC):
        return False
    return invite["sessions_used"] < invite["max_sessions"]


def check_invite(db: firestore.Client, code: str) -> bool:
    return _is_usable(db.collection("invites").document(hash_code(code)).get().to_dict())


@firestore.transactional
def _redeem(
    transaction, db, invite_ref, session_ref, contact_ref, session, contact, limits
) -> bool:
    invite = invite_ref.get(transaction=transaction).to_dict()
    if not _is_usable(invite):
        return False
    # In the same transaction as the write, so two starts at once can't both pass the limit.
    max_calls, max_session_minutes = limits
    if _live_calls(transaction, db, session["created_at"], max_session_minutes) >= max_calls:
        raise LineBusy
    transaction.update(invite_ref, {"sessions_used": invite["sessions_used"] + 1})
    transaction.set(session_ref, session)
    if contact:
        transaction.set(contact_ref, contact)
    return True


def redeem_invite(
    db: firestore.Client,
    code: str,
    terms_version: str,
    terms_language: str,
    contact: dict | None,
    retention_days: int,
    max_concurrent_calls: int,
    max_session_minutes: int,
) -> str | None:
    """Uses one session from the invite and records consent. Returns None if unusable.

    Raises LineBusy when `max_concurrent_calls` calls are already live, and InviteBusy on
    contention. Nothing is written in either case.
    """
    now = datetime.now(UTC)
    delete_at = now + timedelta(days=retention_days)
    invite_id = hash_code(code)
    session_id = secrets.token_urlsafe(16)
    session = {
        "invite_id": invite_id,
        "status": "created",
        "terms_version": terms_version,
        # The language the visitor agreed in, so Lee can show which text they read (ADR-4).
        "terms_language": terms_language,
        "terms_accepted_at": now,
        "created_at": now,
        "delete_at": delete_at,
    }
    # Contact details stay apart from the transcript so each can be handled on its own.
    contact_doc = {**contact, "invite_id": invite_id, "delete_at": delete_at} if contact else None
    try:
        redeemed = _redeem(
            db.transaction(),
            db,
            db.collection("invites").document(invite_id),
            db.collection("sessions").document(session_id),
            db.collection("contacts").document(session_id),
            session,
            contact_doc,
            (max_concurrent_calls, max_session_minutes),
        )
    except Aborted as exc:
        # An abort during the read isn't retried by the library, so it arrives bare.
        raise InviteBusy from exc
    except ValueError as exc:
        # An abort at commit is retried, then wrapped in a ValueError once retries run out.
        if isinstance(exc.__cause__, Aborted):
            raise InviteBusy from exc
        raise
    return session_id if redeemed else None


@firestore.transactional
def _release(transaction, db, session_ref) -> bool:
    snapshot = session_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise NoSuchSession
    data = snapshot.to_dict()
    if data.get("released"):
        return False
    invite_ref = db.collection("invites").document(data["invite_id"])
    invite = invite_ref.get(transaction=transaction)
    now = datetime.now(UTC)
    update: dict = {"released": True, "released_at": now}
    if data["status"] != "ended":
        # Ended here, so the call stops counting as live and no summary is written for it.
        update |= {
            "status": "ended",
            "ended_at": now,
            "end_reason": "agent_failed",
            "summary": "",
            "declined_questions": [],
            "summary_status": "empty",
        }
    transaction.update(session_ref, update)
    if invite.exists:
        used = invite.to_dict()["sessions_used"]
        transaction.update(invite_ref, {"sessions_used": max(used - 1, 0)})
    return True


def release_session(db: firestore.Client, session_id: str) -> bool:
    """Gives a failed call's session back to its invite, once (I7, I9).

    The agent calls this when the call ended before the visitor heard anything. Returns False
    if it was already released, so a replayed request changes nothing (ADR-9). Raises
    NoSuchSession for an unknown ID.
    """
    return _release(db.transaction(), db, db.collection("sessions").document(session_id))


def _invite_view(invite_id: str, invite: dict) -> dict:
    """What admin sees. The code isn't stored, so it can't appear here (ADR-3, ADR-10)."""
    return {
        "id": invite_id,
        "label": invite["label"],
        "sessionLimit": invite["max_sessions"],
        "sessionsUsed": invite["sessions_used"],
        "expiresAt": invite["expires_at"].isoformat(),
        "revoked": invite["revoked"],
    }


def get_invite_view(db: firestore.Client, invite_id: str) -> dict | None:
    snapshot = db.collection("invites").document(invite_id).get()
    return _invite_view(snapshot.id, snapshot.to_dict()) if snapshot.exists else None


def list_invites(db: firestore.Client, limit: int = 200) -> list[dict]:
    query = (
        db.collection("invites")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [_invite_view(s.id, s.to_dict()) for s in query.stream()]


def revoke_invite(db: firestore.Client, invite_id: str) -> dict | None:
    """Stops the code working at once. `delete_at` is unchanged (ADR-6). None if no such invite."""
    ref = db.collection("invites").document(invite_id)
    if not ref.get().exists:
        return None
    ref.update({"revoked": True})
    return get_invite_view(db, invite_id)
