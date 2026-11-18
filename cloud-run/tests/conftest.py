import os
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings, get_settings

# Tests are hermetic: no real config from cloud-run/.env or the shell.
Settings.model_config["env_file"] = None
for name in Settings.model_fields:
    os.environ.pop(name.upper(), None)

os.environ.update(
    LIVEKIT_URL="wss://test.livekit.cloud",
    LIVEKIT_API_KEY="test-key",
    LIVEKIT_API_SECRET="test-secret-that-is-long-enough-for-hs256",
    LIVEKIT_AGENT_NAME="test-agent",
    FIREBASE_PROJECT_ID="demo-portfolio",
    OWNER_NAME="Sam Example",
    TERMS_LEGAL_NAME="Test Legal Name",
    TERMS_CONTACT_EMAIL="privacy@example.com",
    RATE_LIMIT_PER_MINUTE="1000",
    ADMIN_EMAIL="admin@example.com",
    AGENT_SIGNING_SECRET="test-agent-signing-secret-at-least-32-chars",
)

from fastapi.testclient import TestClient

from app import admin_auth
from app.main import app
from app.rate_limit import get_limiter
from app.store import create_invite, get_db
from app.terms import get_terms


@pytest.fixture(scope="session", autouse=True)
def require_emulator():
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.exit("Run through the Firestore emulator. See cloud-run/README.md.", returncode=2)


@pytest.fixture(autouse=True)
def no_call_limit():
    """Tests share one emulator database and leave calls live, so the limit is lifted here.
    tests/test_call_limits.py sets it back to 1 on a cleared database. model_copy skips the
    field's bounds on purpose."""
    settings = get_settings().model_copy(update={"max_concurrent_calls": 1_000_000})
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


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
        return create_invite(db, "Test", max_sessions, datetime.now(UTC) + expires_in, 90)

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


@pytest.fixture(autouse=True)
def fake_google(monkeypatch):
    tokens = {
        "good-token": {"email": "Admin@Example.com", "email_verified": True},
        "other-account": {"email": "someone@example.com", "email_verified": True},
        "unverified": {"email": "admin@example.com", "email_verified": False},
    }

    def verify(token):
        if token not in tokens:
            raise ValueError("invalid token")
        return tokens[token]

    monkeypatch.setattr(admin_auth, "verify_id_token", verify)
