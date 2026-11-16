import json
import os
import time
from pathlib import Path

import pytest

from app import admin_auth
from app.agent_auth import signature
from app.import_facts import read_seed

ADMIN = {"Authorization": "Bearer good-token"}
SECRET = os.environ["AGENT_SIGNING_SECRET"].encode()

FACT = {
    "section": "experience",
    "topic": "Example Co, Engineer",
    "level": "Senior",
    "verified": "Built the thing.",
    "limits": "Don't name clients.",
    "stories": [
        {
            "title": "Migration",
            "situation": "Old system.",
            "task": "Move it.",
            "action": "Moved it.",
            "result": "It moved.",
        }
    ],
}


@pytest.fixture(autouse=True)
def clean_facts(db):
    for name in ("facts", "fact_versions", "fact_meta"):
        for doc in db.collection(name).stream():
            doc.reference.delete()


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


def signed(path, secret=SECRET, timestamp=None, method="GET", body=b""):
    timestamp = str(timestamp or int(time.time()))
    return {
        "X-Agent-Timestamp": timestamp,
        "X-Agent-Signature": signature(secret, timestamp, method, path, body),
    }


def agent_facts(client):
    return client.get("/internal/facts", headers=signed("/internal/facts"))


# Admin sign-in (ADR-10, A3)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "good-token"},
        {"Authorization": "Bearer not-a-real-token"},
        {"Authorization": "Bearer other-account"},
        {"Authorization": "Bearer unverified"},
    ],
    ids=["no token", "no scheme", "invalid token", "wrong account", "unverified email"],
)
def test_admin_refuses_anyone_but_lee(client, headers):
    responses = [
        client.get("/admin/facts", headers=headers),
        client.post("/admin/facts", json=FACT, headers=headers),
        client.post("/admin/facts/publish", headers=headers),
        client.post("/admin/facts/rollback", json={"version": 1}, headers=headers),
        client.delete("/admin/facts/x", headers=headers),
    ]
    assert {r.status_code for r in responses} == {401}
    assert len({r.text for r in responses}) == 1


def test_cors_allows_the_admin_token_header(client):
    response = client.options(
        "/admin/facts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


# Drafts, publishing and rollback (ADR-21, A8)


def test_drafts_never_reach_the_agent(client):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    assert agent_facts(client).status_code == 404

    client.post("/admin/facts/publish", headers=ADMIN)
    draft = {**FACT, "topic": "Unpublished draft", "verified": "Secret draft text."}
    client.post("/admin/facts", json=draft, headers=ADMIN)

    body = agent_facts(client).json()
    assert body["version"] == 1
    assert [f["topic"] for f in body["facts"]] == [FACT["topic"]]
    assert "Secret draft text" not in json.dumps(body)


def test_published_fact_carries_its_stories(client):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    fact = agent_facts(client).json()["facts"][0]
    assert fact == FACT


def test_an_edit_reaches_the_agent_only_after_publishing(client):
    state = client.post("/admin/facts", json=FACT, headers=ADMIN).json()
    client.post("/admin/facts/publish", headers=ADMIN)
    fact_id = state["working"][0]["id"]

    client.put(f"/admin/facts/{fact_id}", json={**FACT, "level": "Staff"}, headers=ADMIN)
    assert agent_facts(client).json()["facts"][0]["level"] == "Senior"

    client.post("/admin/facts/publish", headers=ADMIN)
    live = agent_facts(client).json()
    assert live["version"] == 2
    assert live["facts"][0]["level"] == "Staff"


def test_rollback_restores_the_earlier_set_as_a_new_version(client):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    client.post("/admin/facts", json={**FACT, "topic": "Second"}, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    client.post("/admin/facts", json={**FACT, "topic": "Draft"}, headers=ADMIN)

    state = client.post("/admin/facts/rollback", json={"version": 1}, headers=ADMIN).json()
    assert [v["number"] for v in state["versions"]] == [1, 2, 3]
    # The working set is replaced, so the unpublished draft is gone too.
    assert [f["topic"] for f in state["working"]] == [FACT["topic"]]

    live = agent_facts(client).json()
    assert live["version"] == 3
    assert [f["topic"] for f in live["facts"]] == [FACT["topic"]]


def test_rollback_to_a_missing_version_changes_nothing(client):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    response = client.post("/admin/facts/rollback", json={"version": 9}, headers=ADMIN)
    assert response.status_code == 404
    assert agent_facts(client).json()["version"] == 1


def test_editing_a_missing_fact_is_404(client):
    response = client.put("/admin/facts/nope", json=FACT, headers=ADMIN)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {**FACT, "section": "secrets"},
        {**FACT, "topic": ""},
        {**FACT, "unexpected": "field"},
        {**FACT, "stories": [{"title": "x", "extra": "field"}]},
        {**FACT, "stories": [FACT["stories"][0]] * 11},
    ],
    ids=["bad section", "empty topic", "extra field", "extra story field", "too many stories"],
)
def test_bad_facts_are_rejected(client, bad):
    assert client.post("/admin/facts", json=bad, headers=ADMIN).status_code == 422


def test_facts_are_ordered_by_section(client):
    client.post("/admin/facts", json={**FACT, "section": "not_skills", "topic": "B"}, headers=ADMIN)
    client.post("/admin/facts", json={**FACT, "section": "profile", "topic": "A"}, headers=ADMIN)
    state = client.get("/admin/facts", headers=ADMIN).json()
    assert [f["topic"] for f in state["working"]] == ["A", "B"]


# Signed agent requests (ADR-9)


def test_signed_request_is_accepted(client):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    assert agent_facts(client).status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        signed("/internal/facts", secret=b"wrong-secret-wrong-secret-wrong-secret"),
        signed("/internal/facts", timestamp=int(time.time()) - 400),
        signed("/internal/facts", timestamp=int(time.time()) + 400),
        signed("/internal/other"),
        signed("/internal/facts", method="POST"),
        {"X-Agent-Timestamp": "soon", "X-Agent-Signature": "x"},
    ],
    ids=[
        "unsigned",
        "wrong secret",
        "too old",
        "from the future",
        "other path",
        "other method",
        "bad timestamp",
    ],
)
def test_bad_agent_signatures_are_refused(client, headers):
    client.post("/admin/facts", json=FACT, headers=ADMIN)
    client.post("/admin/facts/publish", headers=ADMIN)
    assert client.get("/internal/facts", headers=headers).status_code == 401


def test_an_admin_token_does_not_open_internal_endpoints(client):
    assert client.get("/internal/facts", headers=ADMIN).status_code == 401


# Seed import (ADR-21)


def test_seed_import_keeps_only_reviewed_entries(tmp_path):
    seed = tmp_path / "seed.yaml"
    seed.write_text(
        """
skills:
  - topic: Reviewed
    level: Pro
    verified: >
      Folded
      text.
    reviewed: true
    stories:
      - title: Story
        situation: S
        task: T
        action: A
        result: R
  - topic: Draft
    reviewed: false
  - topic: No flag
""",
        encoding="utf-8",
    )
    reviewed, skipped = read_seed(seed)
    assert [f.topic for f in reviewed] == ["Reviewed"]
    assert reviewed[0].verified == "Folded text."
    assert reviewed[0].stories[0].result == "R"
    assert skipped == ["Draft", "No flag"]


def test_the_real_seed_file_is_valid():
    reviewed, _ = read_seed(Path(__file__).parents[2] / "livekit" / "facts" / "lee.yaml")
    assert reviewed


def test_signature_matches_the_agent():
    # Pinned in livekit/tests/test_cloud_run.py too, so the two services can't drift apart.
    vector = ("golden-secret-golden-secret-golden-secret", "1800000000", "GET", "/internal/facts")
    secret, timestamp, method, path = vector
    expected = "3c48205d4bc6cd99d227f30885e077e6bacaa57113c3010eb233dba32965275b"
    assert signature(secret.encode(), timestamp, method, path, b"") == expected
