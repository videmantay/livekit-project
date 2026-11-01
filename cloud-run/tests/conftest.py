import os
from datetime import UTC, datetime, timedelta

import pytest

os.environ.update(
    LIVEKIT_URL="wss://test.livekit.cloud",
    LIVEKIT_API_KEY="test-key",
    LIVEKIT_API_SECRET="test-secret-that-is-long-enough-for-hs256",
    LIVEKIT_AGENT_NAME="test-agent",
    FIREBASE_PROJECT_ID="demo-portfolio",
    TERMS_LEGAL_NAME="Test Legal Name",
    TERMS_CONTACT_EMAIL="privacy@example.com",
    RATE_LIMIT_PER_MINUTE="1000",
)

from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import get_limiter
from app.store import create_invite, get_db
from app.terms import get_terms


@pytest.fixture(scope="session", autouse=True)
def require_emulator():
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.exit("Run through the Firestore emulator. See cloud-run/README.md.", returncode=2)


@pytest.fixture
def client():
    get_limiter.cache_clear()
    return TestClient(app)


@pytest.fixture
def db():
    return get_db()


@pytest.fixture
def make_invite(db):
    def _make(max_sessions=2, expires_in=timedelta(days=1)):
        return create_invite(db, "Test", max_sessions, datetime.now(UTC) + expires_in)

    return _make


@pytest.fixture
def session_body():
    def _body(code, **overrides):
        return {
            "code": code,
            "terms_version": get_terms().version,
            "terms_accepted": True,
            **overrides,
        }

    return _body
