from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
from livekit import api
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app import conversations, facts, store
from app.admin_auth import require_admin
from app.agent_auth import require_agent
from app.config import Settings, TermsLanguage, get_settings
from app.livekit_tokens import create_visitor_token
from app.rate_limit import rate_limit
from app.store import InviteBusy, LineBusy, check_invite, get_db, redeem_invite
from app.terms import get_terms

InviteCode = Annotated[str, Field(min_length=1, max_length=64)]
FactId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
# token_urlsafe(16) for sessions, and a SHA-256 hex digest for invites.
SessionId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
InviteId = Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")]
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[firestore.Client, Depends(get_db)]

# One response for every failure, so callers can't tell an expired code from a wrong one.
INVALID_INVITE = HTTPException(status_code=403, detail="Invalid or expired invite")

app = FastAPI(title="Portfolio gatekeeper", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    # Authorization carries the admin's Google ID token (ADR-10).
    allow_headers=["Content-Type", "Authorization"],
    # The frontend reads Retry-After on a busy 503 from POST /sessions (I9).
    expose_headers=["Retry-After"],
)


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=120)


class VerifyInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: InviteCode
    # The visitor's browser preference or their pick. A language not offered gets English.
    language: TermsLanguage = "en"


class StartSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: InviteCode
    terms_version: str = Field(max_length=64)
    terms_language: TermsLanguage = "en"
    terms_accepted: Literal[True]
    contact: Contact | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# The terms come back only for a valid code, behind the same gate and rate limit, so the
# legal name and contact email aren't one public request away (ADR-15).
@app.post("/invites/verify", dependencies=[Depends(rate_limit)])
def verify_invite(body: VerifyInvite, settings: SettingsDep, db: DbDep) -> dict:
    if not check_invite(db, body.code):
        raise INVALID_INVITE
    offered = settings.offered_terms_languages
    terms = get_terms(body.language if body.language in offered else "en")
    return {
        "valid": True,
        "terms": {"version": terms.version, "text": terms.text, "language": terms.language},
        # The frontend shows a language switch only when more than one is offered.
        "languages": offered,
    }


@app.post("/sessions", status_code=201, dependencies=[Depends(rate_limit)])
def start_session(body: StartSession, settings: SettingsDep, db: DbDep) -> dict:
    # A language switched off since the page loaded counts as changed terms, like a new version.
    if (
        body.terms_language not in settings.offered_terms_languages
        or body.terms_version != get_terms(body.terms_language).version
    ):
        raise HTTPException(status_code=409, detail="Terms have changed")
    contact = body.contact.model_dump(exclude_none=True) if body.contact else None
    try:
        session_id = redeem_invite(
            db,
            body.code,
            body.terms_version,
            body.terms_language,
            contact,
            settings.retention_days,
            settings.max_concurrent_calls,
            settings.max_session_minutes,
        )
    except LineBusy:
        # Every call slot is in use (Tavus allows one at a time). Nothing was used, so the
        # visitor can retry; the frontend shows its "line is busy" message (I9).
        raise HTTPException(
            status_code=503, detail="Line busy, try again", headers={"Retry-After": "30"}
        ) from None
    except InviteBusy:
        # Contention on one invite, not a server fault. Nothing was used, so a retry is safe.
        raise HTTPException(
            status_code=503, detail="Busy, try again", headers={"Retry-After": "1"}
        ) from None
    if session_id is None:
        raise INVALID_INVITE
    room, token = create_visitor_token(settings, session_id, body.terms_language)
    return {"room": room, "token": token, "url": settings.livekit_url}


# Admin: Lee's facts (ADR-21, A8). Every route checks the Google sign-in (ADR-10).
admin = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@admin.get("/facts")
def get_facts(db: DbDep) -> dict:
    return facts.facts_state(db)


@admin.post("/facts", status_code=201)
def create_fact(body: facts.FactInput, db: DbDep) -> dict:
    facts.create_fact(db, body)
    return facts.facts_state(db)


@admin.put("/facts/{fact_id}")
def update_fact(fact_id: FactId, body: facts.FactInput, db: DbDep) -> dict:
    if not facts.update_fact(db, fact_id, body):
        raise HTTPException(status_code=404, detail="No such fact")
    return facts.facts_state(db)


@admin.delete("/facts/{fact_id}")
def delete_fact(fact_id: FactId, db: DbDep) -> dict:
    facts.delete_fact(db, fact_id)
    return facts.facts_state(db)


@admin.post("/facts/publish")
def publish_facts(db: DbDep) -> dict:
    facts.publish(db)
    return facts.facts_state(db)


class Rollback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


@admin.post("/facts/rollback")
def rollback_facts(body: Rollback, db: DbDep) -> dict:
    if facts.rollback(db, body.version) is None:
        raise HTTPException(status_code=404, detail="No such version")
    return facts.facts_state(db)


# Internal: called only by the agent, with a signed request (ADR-9).
internal = APIRouter(prefix="/internal", dependencies=[Depends(require_agent)])


@internal.get("/facts")
def published_facts(db: DbDep) -> dict:
    """The live published version, never drafts. The agent fetches this at call start."""
    live = facts.published(db)
    if live is None:
        raise HTTPException(status_code=404, detail="Nothing published")
    return live


@internal.post("/sessions/{session_id}/transcript", status_code=201)
def add_transcript_batch(
    session_id: SessionId, body: conversations.TranscriptBatch, settings: SettingsDep, db: DbDep
) -> dict:
    """One batch of turns from the agent (A4). The final batch ends the call and summarizes it.

    409 for a batch number already stored, including a replayed request, or after the call has
    ended. Nothing is written then, so an agent retry that gets 409 is safe to drop.
    """
    try:
        conversations.add_batch(db, session_id, body)
    except conversations.NoSession:
        raise HTTPException(status_code=404, detail="No such session") from None
    except conversations.Duplicate:
        raise HTTPException(status_code=409, detail="Batch already stored") from None
    except conversations.SessionEnded:
        raise HTTPException(status_code=409, detail="Session has ended") from None
    if body.final:
        conversations.end_session(db, settings, session_id, "agent")
    return {"stored": True}


@internal.post("/sessions/{session_id}/release")
def release_session(session_id: SessionId, db: DbDep) -> dict:
    """The call ended before the visitor heard anything, so its session goes back to the
    invite and the call ends (I7, I9). Once per session: a replay finds it released and
    changes nothing (ADR-9)."""
    try:
        released = store.release_session(db, session_id)
    except store.NoSuchSession:
        raise HTTPException(status_code=404, detail="No such session") from None
    return {"released": released}


# Admin: conversations and invites (A1, A2, A6, A7).


@admin.get("/conversations")
def list_conversations(db: DbDep) -> list[dict]:
    return conversations.list_conversations(db)


@admin.delete("/conversations/{session_id}", status_code=204)
def delete_conversation(session_id: SessionId, db: DbDep) -> Response:
    conversations.delete_conversation(db, session_id)
    return Response(status_code=204)


class NewInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    sessionLimit: int = Field(default=2, ge=1, le=10)
    expiresInDays: int = Field(default=14, ge=1, le=90)


@admin.get("/invites")
def list_invites(db: DbDep) -> list[dict]:
    return store.list_invites(db)


@admin.post("/invites", status_code=201)
def create_invite(body: NewInvite, settings: SettingsDep, db: DbDep, response: Response) -> dict:
    """The code is in this response only. It isn't stored, so it can't be shown again (A1)."""
    expires_at = datetime.now(UTC) + timedelta(days=body.expiresInDays)
    code, invite_id = store.create_invite(
        db, body.label.strip(), body.sessionLimit, expires_at, settings.retention_days
    )
    response.headers["Cache-Control"] = "no-store"
    return {"invite": store.get_invite_view(db, invite_id), "code": code}


@admin.post("/invites/{invite_id}/revoke")
def revoke_invite(invite_id: InviteId, db: DbDep) -> dict:
    invite = store.revoke_invite(db, invite_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="No such invite")
    return invite


app.include_router(admin)
app.include_router(internal)


# LiveKit's webhook, the fallback that ends a call if the agent dies (ADR-9, A4). LiveKit signs
# each request with the project's API key: a JWT in Authorization that carries the body's
# SHA-256. A replayed room_finished finds the session already ended and changes nothing.
@app.post("/webhooks/livekit")
async def livekit_webhook(
    request: Request,
    settings: SettingsDep,
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    receiver = api.WebhookReceiver(
        api.TokenVerifier(settings.livekit_api_key, settings.livekit_api_secret.get_secret_value())
    )
    try:
        event = receiver.receive((await request.body()).decode(), authorization or "")
    except Exception:  # noqa: BLE001 - the library raises bare Exceptions; the reason isn't returned
        raise HTTPException(status_code=401, detail="Bad signature") from None
    if event.event != "room_finished":
        return {"handled": False}
    session_id = conversations.session_id_from_room(event.room.name)
    if session_id is None:
        return {"handled": False}
    return {"handled": conversations.end_session(db, settings, session_id, "room_finished")}
