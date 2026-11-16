"""Signed requests from the agent to cloud-run's /internal/* endpoints (ADR-2, ADR-9).

The agent never touches Firestore. It signs `timestamp, method, path, sha256(body)` with
HMAC-SHA256 and AGENT_SIGNING_SECRET, the same way cloud-run/app/agent_auth.py checks it.
Change both together. tests/test_cloud_run.py pins a vector that cloud-run's tests share.
"""

import hashlib
import hmac
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
