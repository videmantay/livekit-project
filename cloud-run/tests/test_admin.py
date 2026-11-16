"""Admin conversations and invites (A1, A2, A6, A7). Sign-in itself is tested in test_facts.py."""

import json

import pytest
from helpers import ADMIN, signed

from app import conversations, summary
from app.store import hash_code


@pytest.fixture(autouse=True)
def no_model_or_email(monkeypatch):
    monkeypatch.setattr(
        summary,
        "generate",
        lambda turns: summary.Summary(summary="Short call.", declined_questions=["Go?"]),
    )
    monkeypatch.setattr(conversations, "notify_admin", lambda settings: None)


@pytest.fixture(autouse=True)
def clean(db):
    for name in ("sessions", "contacts", "invites"):
        for doc in db.collection(name).stream():
            db.recursive_delete(doc.reference)


def start(client, make_invite, session_body, contact=None):
    code, invite_id = make_invite()
    body = session_body(code, **({"contact": contact} if contact else {}))
    return client.post("/sessions", json=body).json()["room"].removeprefix("session-"), invite_id


def finish(client, session_id, turns):
    path = f"/internal/sessions/{session_id}/transcript"
    raw = json.dumps({"batch": 0, "turns": turns, "final": True, "facts_version": 2}).encode()
    headers = {"Content-Type": "application/json", **signed(path, method="POST", body=raw)}
    assert client.post(path, content=raw, headers=headers).status_code == 201


TURNS = [
    {"speaker": "agent", "text": "Hi, I'm an AI avatar."},
    {"speaker": "visitor", "text": "Do you know Go?"},
]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin/conversations"),
        ("DELETE", "/admin/conversations/abc"),
        ("GET", "/admin/invites"),
        ("POST", "/admin/invites"),
        ("POST", f"/admin/invites/{'0' * 64}/revoke"),
    ],
)
@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer other-account"}], ids=["none", "wrong account"]
)
def test_admin_endpoints_need_the_admin(client, method, path, headers):
    response = client.request(method, path, headers=headers, json={"label": "x"})
    assert response.status_code == 401


# Conversations (A6)


def test_conversation_lists_summary_transcript_and_contact(client, make_invite, session_body):
    contact = {"name": "Pat", "email": "pat@example.com"}
    session_id, _ = start(client, make_invite, session_body, contact)
    finish(client, session_id, TURNS)

    [c] = client.get("/admin/conversations", headers=ADMIN).json()
    assert c["id"] == session_id
    assert c["inviteLabel"] == "Test"
    assert c["status"] == "ended"
    assert c["summary"] == "Short call."
    assert c["summaryStatus"] == "done"
    assert c["declinedQuestions"] == ["Go?"]
    assert c["factsVersion"] == 2
    assert c["transcript"][1] == {
        "speaker": "visitor",
        "text": "Do you know Go?",
        "violation": False,
    }
    assert c["contact"] == {"name": "Pat", "email": "pat@example.com"}
    assert c["durationSeconds"] >= 0


def test_conversation_without_contact_or_call(client, make_invite, session_body):
    start(client, make_invite, session_body)
    [c] = client.get("/admin/conversations", headers=ADMIN).json()
    assert "contact" not in c
    assert c["transcript"] == []
    assert c["status"] == "created"


def test_conversations_never_show_codes_or_internal_fields(client, make_invite, session_body):
    _, invite_id = start(client, make_invite, session_body)
    text = client.get("/admin/conversations", headers=ADMIN).text
    assert "delete_at" not in text
    assert invite_id not in text


# Deleting one person's data (A7)


def test_delete_removes_session_transcript_summary_and_contact(
    client, db, make_invite, session_body
):
    session_id, invite_id = start(client, make_invite, session_body, {"email": "pat@example.com"})
    finish(client, session_id, TURNS)
    other_id, _ = start(client, make_invite, session_body, {"email": "kim@example.com"})

    assert client.delete(f"/admin/conversations/{session_id}", headers=ADMIN).status_code == 204

    session_ref = db.collection("sessions").document(session_id)
    assert not session_ref.get().exists
    assert list(session_ref.collection("transcript").stream()) == []
    assert not db.collection("contacts").document(session_id).get().exists
    # Other people's data and the invite stay.
    assert db.collection("contacts").document(other_id).get().exists
    assert db.collection("invites").document(invite_id).get().exists
    assert [c["id"] for c in client.get("/admin/conversations", headers=ADMIN).json()] == [other_id]


def test_deleted_session_takes_no_more_batches(client, make_invite, session_body):
    session_id, _ = start(client, make_invite, session_body)
    client.delete(f"/admin/conversations/{session_id}", headers=ADMIN)
    path = f"/internal/sessions/{session_id}/transcript"
    raw = json.dumps({"batch": 1, "turns": TURNS}).encode()
    headers = {"Content-Type": "application/json", **signed(path, method="POST", body=raw)}
    assert client.post(path, content=raw, headers=headers).status_code == 404


def test_delete_is_idempotent(client):
    assert client.delete("/admin/conversations/never-existed", headers=ADMIN).status_code == 204


# Invites (A1, A2)


def test_created_invite_code_works_once_shown(client, db, session_body):
    response = client.post(
        "/admin/invites",
        headers=ADMIN,
        json={"label": " Acme recruiter ", "sessionLimit": 1, "expiresInDays": 7},
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    code, invite = body["code"], body["invite"]
    assert invite["label"] == "Acme recruiter"
    assert invite["sessionLimit"] == 1
    assert invite["sessionsUsed"] == 0
    assert invite["revoked"] is False
    assert invite["id"] == hash_code(code)

    assert client.post("/sessions", json=session_body(code)).status_code == 201
    # The code is never stored or listed again.
    listed = client.get("/admin/invites", headers=ADMIN).text
    assert code not in listed
    assert code not in json.dumps(
        db.collection("invites").document(invite["id"]).get().to_dict(), default=str
    )
    assert client.get("/admin/invites", headers=ADMIN).json()[0]["sessionsUsed"] == 1


def test_invite_defaults(client):
    invite = client.post("/admin/invites", headers=ADMIN, json={"label": "x"}).json()["invite"]
    assert invite["sessionLimit"] == 2


@pytest.mark.parametrize(
    "bad",
    [
        {"label": ""},
        {"label": "x" * 121},
        {"label": "x", "sessionLimit": 0},
        {"label": "x", "sessionLimit": 11},
        {"label": "x", "expiresInDays": 0},
        {"label": "x", "expiresInDays": 91},
        {"label": "x", "code": "my-own-code"},
    ],
)
def test_bad_invites_are_rejected(client, db, bad):
    assert client.post("/admin/invites", headers=ADMIN, json=bad).status_code == 422
    assert list(db.collection("invites").stream()) == []


def test_revoke_stops_the_code_at_once(client, session_body):
    body = client.post("/admin/invites", headers=ADMIN, json={"label": "x"}).json()
    code, invite_id = body["code"], body["invite"]["id"]

    response = client.post(f"/admin/invites/{invite_id}/revoke", headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["revoked"] is True
    assert client.post("/invites/verify", json={"code": code}).status_code == 403
    assert client.post("/sessions", json=session_body(code)).status_code == 403


def test_revoking_a_missing_invite_is_404(client):
    response = client.post(f"/admin/invites/{'a' * 64}/revoke", headers=ADMIN)
    assert response.status_code == 404


def test_invites_are_listed_newest_first(client):
    for label in ("first", "second"):
        client.post("/admin/invites", headers=ADMIN, json={"label": label})
    labels = [i["label"] for i in client.get("/admin/invites", headers=ADMIN).json()]
    assert labels == ["second", "first"]
