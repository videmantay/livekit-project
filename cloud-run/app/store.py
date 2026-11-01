import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from google.cloud import firestore

from app.config import get_settings


@lru_cache
def get_db() -> firestore.Client:
    return firestore.Client(project=get_settings().firebase_project_id)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_invite(
    db: firestore.Client, label: str, max_sessions: int, expires_at: datetime
) -> tuple[str, str]:
    """Returns (code, invite_id). The code is never stored, so it can't be shown again."""
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
def _redeem(transaction, invite_ref, session_ref, contact_ref, session, contact) -> bool:
    invite = invite_ref.get(transaction=transaction).to_dict()
    if not _is_usable(invite):
        return False
    transaction.update(invite_ref, {"sessions_used": invite["sessions_used"] + 1})
    transaction.set(session_ref, session)
    if contact:
        transaction.set(contact_ref, contact)
    return True


def redeem_invite(
    db: firestore.Client,
    code: str,
    terms_version: str,
    contact: dict | None,
    retention_days: int,
) -> str | None:
    """Uses one session from the invite and records consent. Returns None if unusable."""
    now = datetime.now(UTC)
    delete_at = now + timedelta(days=retention_days)
    invite_id = hash_code(code)
    session_id = secrets.token_urlsafe(16)
    session = {
        "invite_id": invite_id,
        "status": "created",
        "terms_version": terms_version,
        "terms_accepted_at": now,
        "created_at": now,
        "delete_at": delete_at,
    }
    # Contact details stay apart from the transcript so each can be handled on its own.
    contact_doc = {**contact, "invite_id": invite_id, "delete_at": delete_at} if contact else None
    redeemed = _redeem(
        db.transaction(),
        db.collection("invites").document(invite_id),
        db.collection("sessions").document(session_id),
        db.collection("contacts").document(session_id),
        session,
        contact_doc,
    )
    return session_id if redeemed else None
