"""Signed requests from the agent to /internal/* (ADR-9).

The agent signs `timestamp, method, path, sha256(body)` with HMAC-SHA256 and a secret shared
only by the two services. Requests outside a five-minute window are refused, which limits replays.
That's enough for reads, which change nothing. Transcript batches will add a stored nonce, so the
same batch can't be written twice.

livekit/cloud_run.py signs the same way. Change both together.
"""

import hashlib
import hmac
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from app.config import Settings, get_settings

MAX_SKEW_SECONDS = 300

NOT_SIGNED = HTTPException(status_code=401, detail="Bad signature")


def signature(secret: bytes, timestamp: str, method: str, path: str, body: bytes) -> str:
    message = "\n".join((timestamp, method.upper(), path, hashlib.sha256(body).hexdigest()))
    return hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()


async def require_agent(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    x_agent_timestamp: Annotated[str | None, Header()] = None,
    x_agent_signature: Annotated[str | None, Header()] = None,
) -> None:
    if not x_agent_timestamp or not x_agent_signature:
        raise NOT_SIGNED
    try:
        sent_at = int(x_agent_timestamp)
    except ValueError:
        raise NOT_SIGNED from None
    if abs(time.time() - sent_at) > MAX_SKEW_SECONDS:
        raise NOT_SIGNED
    expected = signature(
        settings.agent_signing_secret.get_secret_value().encode(),
        x_agent_timestamp,
        request.method,
        request.url.path,
        await request.body(),
    )
    if not hmac.compare_digest(expected, x_agent_signature):
        raise NOT_SIGNED
