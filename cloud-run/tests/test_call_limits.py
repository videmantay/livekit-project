"""One call at a time, and a failed call's session given back to the invite (I7, I9)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from helpers import signed

from app.config import get_settings
from app.main import app
from app.store import LIVE_CALL_GRACE


@pytest.fixture(autouse=True)
def one_call_at_a_time(db):
    """A cleared database and the production limit of one live call."""
    for doc in db.collection("sessions").stream():
        doc.reference.delete()
    # Replaces conftest's lifted limit; conftest removes the override afterwards.
    settings = get_settings().model_copy(update={"max_concurrent_calls": 1})
    app.dependency_overrides[get_settings] = lambda: settings


def start(client, session_body, code):
    return client.post("/sessions", json=session_body(code))


def release(client, session_id, **sign_args):
    path = f"/internal/sessions/{session_id}/release"
    return client.post(path, headers=signed(path, method="POST", **sign_args))


def sessions_used(db, invite_id):
    return db.collection("invites").document(invite_id).get().to_dict()["sessions_used"]


def session_id_of(response):
    return response.json()["room"].removeprefix("session-")


def test_second_call_is_refused_while_one_is_live_and_uses_no_session(
    client, db, make_invite, session_body
):
    first_code, _ = make_invite()
    second_code, second_invite = make_invite()
    assert start(client, session_body, first_code).status_code == 201

    response = start(client, session_body, second_code)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    assert sessions_used(db, second_invite) == 0


def test_a_call_can_start_once_the_live_one_ends(client, db, make_invite, session_body):
    code, _ = make_invite(max_sessions=2)
    first = start(client, session_body, code)
    db.collection("sessions").document(session_id_of(first)).update({"status": "ended"})

    assert start(client, session_body, code).status_code == 201


def test_a_call_that_never_ended_stops_counting_after_the_longest_call(
    client, db, make_invite, session_body
):
    # A visitor who never joined gets no room_finished, so the session never ends by itself.
    code, _ = make_invite(max_sessions=2)
    first = start(client, session_body, code)
    too_old = timedelta(minutes=get_settings().max_session_minutes) + LIVE_CALL_GRACE
    db.collection("sessions").document(session_id_of(first)).update(
        {"created_at": datetime.now(UTC) - too_old - timedelta(seconds=5)}
    )

    assert start(client, session_body, code).status_code == 201


def test_release_gives_the_session_back_and_frees_the_line(
    client, db, make_invite, session_body
):
    code, invite_id = make_invite(max_sessions=1)
    session_id = session_id_of(start(client, session_body, code))
    assert sessions_used(db, invite_id) == 1

    response = release(client, session_id)

    assert response.status_code == 200
    assert response.json() == {"released": True}
    assert sessions_used(db, invite_id) == 0
    session = db.collection("sessions").document(session_id).get().to_dict()
    assert session["status"] == "ended"
    assert session["end_reason"] == "agent_failed"
    # The invite works again, and the line is free for it.
    assert start(client, session_body, code).status_code == 201


def test_release_happens_once(client, db, make_invite, session_body):
    code, invite_id = make_invite(max_sessions=2)
    session_id = session_id_of(start(client, session_body, code))
    db.collection("sessions").document(session_id).update({"status": "ended"})
    start(client, session_body, code)
    assert sessions_used(db, invite_id) == 2

    assert release(client, session_id).json() == {"released": True}
    # A replay inside the signature window changes nothing (ADR-9).
    assert release(client, session_id).json() == {"released": False}
    assert sessions_used(db, invite_id) == 1


def test_release_after_the_call_ended_keeps_its_end(client, db, make_invite, session_body):
    code, invite_id = make_invite()
    session_id = session_id_of(start(client, session_body, code))
    ref = db.collection("sessions").document(session_id)
    ref.update({"status": "ended", "end_reason": "agent", "summary_status": "empty"})

    assert release(client, session_id).json() == {"released": True}

    assert ref.get().to_dict()["end_reason"] == "agent"
    assert sessions_used(db, invite_id) == 0


def test_release_of_an_unknown_session_is_404(client):
    assert release(client, "no-such-session").status_code == 404


@pytest.mark.parametrize(
    "sign_args", [{"secret": b"wrong-secret-that-is-long-enough!!"}, {"timestamp": 1}]
)
def test_forged_release_is_refused(client, db, make_invite, session_body, sign_args):
    code, invite_id = make_invite()
    session_id = session_id_of(start(client, session_body, code))

    assert release(client, session_id, **sign_args).status_code == 401
    assert sessions_used(db, invite_id) == 1


def test_unsigned_release_is_refused(client, db, make_invite, session_body):
    code, _ = make_invite()
    session_id = session_id_of(start(client, session_body, code))

    response = client.post(f"/internal/sessions/{session_id}/release")

    assert response.status_code == 401
    assert json.loads(response.content)["detail"] == "Bad signature"
