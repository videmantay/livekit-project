from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.config import Settings, get_settings
from app.livekit_tokens import create_visitor_token
from app.rate_limit import rate_limit
from app.store import check_invite, get_db, redeem_invite
from app.terms import get_terms

InviteCode = Annotated[str, Field(min_length=1, max_length=64)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[firestore.Client, Depends(get_db)]

# One response for every failure, so callers can't tell an expired code from a wrong one.
INVALID_INVITE = HTTPException(status_code=403, detail="Invalid or expired invite")

app = FastAPI(title="Portfolio gatekeeper", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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


@app.get("/terms")
def read_terms() -> dict:
    terms = get_terms()
    return {"version": terms.version, "text": terms.text}


@app.post("/invites/verify", dependencies=[Depends(rate_limit)])
def verify_invite(body: VerifyInvite, db: DbDep) -> dict:
    if not check_invite(db, body.code):
        raise INVALID_INVITE
    return {"valid": True}


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
