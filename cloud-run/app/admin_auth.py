"""Admin sign-in: a Google ID token from Firebase Auth, checked on every request (ADR-10, A3)."""

from functools import lru_cache
from typing import Annotated

import firebase_admin
from fastapi import Depends, Header, HTTPException
from firebase_admin import auth, exceptions

from app.config import Settings, get_settings

# One response for every failure, so a caller can't tell a bad token from the wrong account.
NOT_ADMIN = HTTPException(status_code=401, detail="Not signed in as admin")


@lru_cache
def _firebase_app() -> firebase_admin.App:
    # Verifying ID tokens needs only the project ID, not a service account.
    return firebase_admin.initialize_app(options={"projectId": get_settings().firebase_project_id})


def verify_id_token(token: str) -> dict:
    return auth.verify_id_token(token, app=_firebase_app())


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise NOT_ADMIN
    try:
        claims = verify_id_token(token)
    except ValueError, exceptions.FirebaseError:
        # Expired, revoked, malformed or for another project. The reason isn't returned or logged.
        raise NOT_ADMIN from None
    email = str(claims.get("email", "")).lower()
    if not claims.get("email_verified") or email != settings.admin_email.strip().lower():
        raise NOT_ADMIN
