import json
import re
import sys
from datetime import UTC, datetime, timedelta

import pytest

from app import create_invite
from app.store import hash_code


def run_cli(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["create_invite", *args])
    create_invite.main()
    out = capsys.readouterr().out
    code = re.search(r"^Code \(shown once\): (\S+)$", out, re.MULTILINE).group(1)
    invite_id = re.search(r"^Invite ID: (\S+)$", out, re.MULTILINE).group(1)
    return code, invite_id, out


def test_cli_creates_a_usable_invite_from_its_arguments(
    monkeypatch, capsys, client, db, session_body
):
    code, invite_id, out = run_cli(
        monkeypatch, capsys, "--label", "CLI test", "--max-sessions", "3", "--expires-days", "7"
    )
    stored = db.collection("invites").document(invite_id).get().to_dict()

    assert invite_id == hash_code(code)
    assert len(code) >= 24
    assert stored["label"] == "CLI test"
    assert stored["max_sessions"] == 3
    assert stored["sessions_used"] == 0
    assert stored["revoked"] is False
    expected_expiry = datetime.now(UTC) + timedelta(days=7)
    assert abs(stored["expires_at"] - expected_expiry) < timedelta(minutes=1)
    assert (stored["delete_at"] - stored["expires_at"]).days == 90
    assert f"Expires: {expected_expiry:%Y-%m-%d}" in out

    # The printed code is the real one, and only its hash is stored.
    assert code not in json.dumps(stored, default=str)
    assert client.post("/sessions", json=session_body(code)).status_code == 201


def test_cli_defaults(monkeypatch, capsys, db):
    _, invite_id, _ = run_cli(monkeypatch, capsys, "--label", "Defaults")
    stored = db.collection("invites").document(invite_id).get().to_dict()
    assert stored["max_sessions"] == 2
    expected_expiry = datetime.now(UTC) + timedelta(days=14)
    assert abs(stored["expires_at"] - expected_expiry) < timedelta(minutes=1)


def test_cli_requires_a_label(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["create_invite"])
    with pytest.raises(SystemExit) as exit_info:
        create_invite.main()
    assert exit_info.value.code == 2
    assert "--label" in capsys.readouterr().err
