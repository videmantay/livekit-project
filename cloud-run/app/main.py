from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app import facts
from app.admin_auth import require_admin
from app.agent_auth import require_agent
from app.config import Settings, get_settings
from app.livekit_tokens import create_visitor_token
from app.rate_limit import rate_limit
from app.store import check_invite, get_db, redeem_invite
from app.terms import get_terms

InviteCode = Annotated[str, Field(min_length=1, max_length=64)]
FactId = Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
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
)


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=120)


class VerifyInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: InviteCode


class StartSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: InviteCode
    terms_version: str = Field(max_length=64)
    terms_accepted: Literal[True]
    contact: Contact | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# The terms come back only for a valid code, behind the same gate and rate limit, so the
# legal name and contact email aren't one public request away (ADR-15).
@app.post("/invites/verify", dependencies=[Depends(rate_limit)])
def verify_invite(body: VerifyInvite, db: DbDep) -> dict:
    if not check_invite(db, body.code):
        raise INVALID_INVITE
    terms = get_terms()
    return {"valid": True, "terms": {"version": terms.version, "text": terms.text}}


@app.post("/sessions", status_code=201, dependencies=[Depends(rate_limit)])
def start_session(body: StartSession, settings: SettingsDep, db: DbDep) -> dict:
    if body.terms_version != get_terms().version:
        raise HTTPException(status_code=409, detail="Terms have changed")
    contact = body.contact.model_dump(exclude_none=True) if body.contact else None
    session_id = redeem_invite(db, body.code, body.terms_version, contact, settings.retention_days)
    if session_id is None:
        raise INVALID_INVITE
    room, token = create_visitor_token(settings, session_id)
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


app.include_router(admin)
app.include_router(internal)
