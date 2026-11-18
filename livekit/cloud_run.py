"""Signed requests from the agent to cloud-run's /internal/* endpoints (ADR-2, ADR-9).

The agent never touches Firestore. It signs `timestamp, method, path, sha256(body)` with
HMAC-SHA256 and AGENT_SIGNING_SECRET, the same way cloud-run/app/agent_auth.py checks it.
Change both together. tests/test_cloud_run.py pins a vector that cloud-run's tests share.
"""

import hashlib
import hmac
import json
import time

import aiohttp

FETCH_TIMEOUT_SECONDS = 5.0


def signature(secret: bytes, timestamp: str, method: str, path: str, body: bytes) -> str:
    message = "\n".join((timestamp, method.upper(), path, hashlib.sha256(body).hexdigest()))
    return hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()


def signed_headers(secret: bytes, method: str, path: str, body: bytes = b"") -> dict[str, str]:
    timestamp = str(int(time.time()))
    return {
        "X-Agent-Timestamp": timestamp,
        "X-Agent-Signature": signature(secret, timestamp, method, path, body),
    }


async def fetch_published_facts(base_url: str, secret: bytes) -> dict | None:
    """The live published facts, or None if Lee hasn't published any. Raises on other errors."""
    path = "/internal/facts"
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_SECONDS)
    async with (
        aiohttp.ClientSession(timeout=timeout) as http,
        http.get(base_url.rstrip("/") + path, headers=signed_headers(secret, "GET", path)) as resp,
    ):
        if resp.status == 404:
            return None
        resp.raise_for_status()
        return await resp.json()


async def release_session(base_url: str, secret: bytes, session_id: str, timeout: float) -> int:
    """Gives a failed call's session back to its invite (I7, I9). Returns the HTTP status:
    200 whether or not it was already released. Raises on network errors only."""
    path = f"/internal/sessions/{session_id}/release"
    headers = signed_headers(secret, "POST", path)
    async with (
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as http,
        http.post(base_url.rstrip("/") + path, headers=headers) as resp,
    ):
        return resp.status


async def post_transcript_batch(
    base_url: str, secret: bytes, session_id: str, batch: dict, timeout: float
) -> int:
    """Sends one transcript batch and returns the HTTP status. Raises on network errors only.

    The body is signed byte for byte, so it's serialized here and sent as is.
    """
    path = f"/internal/sessions/{session_id}/transcript"
    body = json.dumps(batch, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json", **signed_headers(secret, "POST", path, body)}
    async with (
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as http,
        http.post(base_url.rstrip("/") + path, data=body, headers=headers) as resp,
    ):
        # The body is never read or logged: it could echo the request (ADR-14).
        return resp.status
