"""Shared by the test files. Fixtures are in conftest.py."""

import os
import time

from app.agent_auth import signature

ADMIN = {"Authorization": "Bearer good-token"}
SECRET = os.environ["AGENT_SIGNING_SECRET"].encode()


def signed(path, secret=SECRET, timestamp=None, method="GET", body=b""):
    """Headers the agent would send, as livekit/cloud_run.py signs them."""
    timestamp = str(timestamp or int(time.time()))
    return {
        "X-Agent-Timestamp": timestamp,
        "X-Agent-Signature": signature(secret, timestamp, method, path, body),
    }
