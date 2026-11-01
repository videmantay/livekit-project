import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.rate_limit import RateLimiter, client_ip
from app.store import hash_code
from app.terms import get_terms

SECRET = os.environ["LIVEKIT_API_SECRET"]


def invite(db, invite_id):
    return db.collection("invites").document(invite_id).get().to_dict()


def test_terms_show_settings_and_ai_disclosure(client):
    body = client.get("/terms").json()
    assert body["version"] == get_terms().version
    assert "Test Legal Name" in body["text"]
    assert "privacy@example.com" in body["text"]
    assert "90 days" in body["text"]
    assert "AI avatar" in body["text"]
    assert "$" not in body["text"]


def test_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_verify_does_not_use_a_session(client, db, make_invite):
    code, invite_id = make_invite()
    assert client.post("/invites/verify", json={"code": code}).status_code == 200
    assert invite(db, invite_id)["sessions_used"] == 0


def test_every_bad_invite_gets_the_same_response(client, db, make_invite):
    expired, _ = make_invite(expires_in=timedelta(seconds=-1))
    revoked, revoked_id = make_invite()
    db.collection("invites").document(revoked_id).update({"revoked": True})
    used, _ = make_invite(max_sessions=0)

    responses = [
        client.post("/invites/verify", json={"code": code})
        for code in ("no-such-code", expired, revoked, used)
    ]
    assert {r.status_code for r in responses} == {403}
    assert len({r.text for r in responses}) == 1


def test_code_is_never_stored(db, make_invite):
    code, invite_id = make_invite()
    assert invite_id == hash_code(code)
    assert code not in json.dumps(invite(db, invite_id), default=str)


def test_session_records_consent(client, db, make_invite, session_body):
    code, invite_id = make_invite()
    response = client.post("/sessions", json=session_body(code))
    assert response.status_code == 201

    session_id = response.json()["room"].removeprefix("session-")
    session = db.collection("sessions").document(session_id).get().to_dict()
    assert session["invite_id"] == invite_id
    assert session["terms_version"] == get_terms().version
    assert session["terms_accepted_at"] is not None
    assert (session["delete_at"] - session["created_at"]).days == 90
    assert invite(db, invite_id)["sessions_used"] == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"terms_accepted": False},
        {"terms_accepted": "true"},
        {"contact": {"email": "not-an-email"}},
        {"contact": {"nickname": "unexpected"}},
    ],
)
def test_bad_requests_get_no_token_and_use_no_session(
    client, db, make_invite, session_body, overrides
):
    code, invite_id = make_invite()
    response = client.post("/sessions", json=session_body(code, **overrides))
    assert response.status_code == 422
    assert "token" not in response.json()
    assert invite(db, invite_id)["sessions_used"] == 0


def test_missing_consent_gets_no_token(client, make_invite):
    code, _ = make_invite()
    response = client.post("/sessions", json={"code": code, "terms_version": get_terms().version})
    assert response.status_code == 422


def test_outdated_terms_are_rejected(client, db, make_invite, session_body):
    code, invite_id = make_invite()
    response = client.post("/sessions", json=session_body(code, terms_version="old"))
    assert response.status_code == 409
    assert invite(db, invite_id)["sessions_used"] == 0


def test_contact_is_stored_apart_from_session(client, db, make_invite, session_body):
    code, invite_id = make_invite()
    contact = {"name": "Pat", "email": "pat@example.com", "company": "Acme"}
    response = client.post("/sessions", json=session_body(code, contact=contact))

    session_id = response.json()["room"].removeprefix("session-")
    stored = db.collection("contacts").document(session_id).get().to_dict()
    assert stored["email"] == "pat@example.com"
    assert stored["invite_id"] == invite_id
    assert stored["delete_at"] is not None
    session = db.collection("sessions").document(session_id).get().to_dict()
    assert "pat@example.com" not in json.dumps(session, default=str)


def test_no_contact_writes_no_contact_doc(client, db, make_invite, session_body):
    code, _ = make_invite()
    response = client.post("/sessions", json=session_body(code))
    session_id = response.json()["room"].removeprefix("session-")
    assert not db.collection("contacts").document(session_id).get().exists


def test_token_is_limited_to_one_room_and_the_microphone(client, make_invite, session_body):
    code, _ = make_invite()
    body = client.post("/sessions", json=session_body(code)).json()
    claims = jwt.decode(body["token"], SECRET, algorithms=["HS256"], options={"verify_aud": False})

    video = claims["video"]
    assert video["room"] == body["room"]
    assert video["roomJoin"] is True
    assert video["canPublishSources"] == ["microphone"]
    assert video["canPublishData"] is False
    for admin_grant in ("roomAdmin", "roomCreate", "roomList", "roomRecord"):
        assert not video.get(admin_grant)
    assert claims["exp"] - claims["nbf"] == 300

    agent = claims["roomConfig"]["agents"][0]
    assert agent["agentName"] == "test-agent"
    metadata = json.loads(agent["metadata"])
    assert metadata["session_id"] == body["room"].removeprefix("session-")
    assert metadata["max_session_minutes"] == 15


def test_sessions_get_separate_rooms(client, make_invite, session_body):
    code, _ = make_invite()
    first = client.post("/sessions", json=session_body(code)).json()
    second = client.post("/sessions", json=session_body(code)).json()
    assert first["room"] != second["room"]


def test_session_limit_is_enforced(client, make_invite, session_body):
    code, _ = make_invite(max_sessions=1)
    assert client.post("/sessions", json=session_body(code)).status_code == 201
    assert client.post("/sessions", json=session_body(code)).status_code == 403


def test_concurrent_redemption_cannot_exceed_the_limit(db, make_invite, session_body):
    code, invite_id = make_invite(max_sessions=1)
    body = session_body(code)

    def attempt(_):
        with TestClient(app) as thread_client:
            return thread_client.post("/sessions", json=body).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(attempt, range(8)))

    assert statuses.count(201) == 1
    assert invite(db, invite_id)["sessions_used"] == 1


def test_cors_allows_only_configured_origins(client):
    headers = {"Access-Control-Request-Method": "POST"}
    good = client.options("/sessions", headers={"Origin": "http://localhost:5173", **headers})
    bad = client.options("/sessions", headers={"Origin": "https://evil.example", **headers})
    assert good.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


@pytest.mark.parametrize("collection", ["invites", "sessions", "contacts"])
def test_firestore_rules_deny_browsers(collection):
    # A request with no Authorization header is judged by the rules, like a browser's.
    base = (
        f"http://{os.environ['FIRESTORE_EMULATOR_HOST']}/v1/projects/demo-portfolio"
        f"/databases/(default)/documents/{collection}"
    )
    assert httpx.get(f"{base}/anything").status_code == 403
    write = httpx.patch(f"{base}/anything", json={"fields": {}})
    assert write.status_code == 403


def test_rate_limiter_blocks_then_recovers():
    limiter = RateLimiter(limit=2, window_seconds=0.05)
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    import time

    time.sleep(0.06)
    assert limiter.allow("a")


def test_client_ip_ignores_spoofed_forwarded_entries():
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"1.1.1.1, 2.2.2.2, 3.3.3.3")],
        "client": ("10.0.0.1", 1),
    }
    assert client_ip(Request(scope)) == "3.3.3.3"
