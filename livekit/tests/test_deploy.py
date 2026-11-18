from deploy import (
    FAILED_POLLS,
    STABLE_SECONDS,
    RolloutWatch,
    current_version,
    deployment_state,
    missing_secrets,
    required_secrets,
)


def test_every_required_setting_is_a_required_secret():
    # The 2026-11-18 crash loop: a required setting with no secret in LiveKit Cloud.
    assert "ELEVENLABS_SPANISH_VOICE_ID" in required_secrets()
    assert {"ELEVENLABS_VOICE_ID", "TAVUS_API_KEY", "TAVUS_FACE_ID"} <= required_secrets()


def test_settings_with_defaults_are_not_required():
    assert "LIVEKIT_AGENT_NAME" not in required_secrets()


def test_missing_secrets_are_listed():
    assert missing_secrets({"A", "B", "C"}, {"B"}) == ["A", "C"]
    assert missing_secrets({"A"}, {"A", "EXTRA"}) == []


def test_current_version():
    versions = {"versions": [{"version": "old"}, {"version": "new", "current": True}]}
    assert current_version(versions) == "new"
    assert current_version({"versions": []}) is None


def test_deployment_state():
    status = {"agents": [{"agentDeployments": [{"version": "v1", "status": "Running"}]}]}
    assert deployment_state(status) == ("v1", "Running")
    assert deployment_state({"agents": []}) == (None, None)


def test_ignores_the_old_versions_status():
    # LiveKit Cloud can report the previous version's stale CrashLoop during a rollout.
    watch = RolloutWatch("new")
    for t in range(10):
        assert watch.update("old", "CrashLoop", t * 10) == "waiting"


def test_ok_only_after_running_for_the_stable_window():
    watch = RolloutWatch("new")
    assert watch.update("new", "Running", 0) == "waiting"
    assert watch.update("new", "Running", STABLE_SECONDS - 1) == "waiting"
    assert watch.update("new", "Running", STABLE_SECONDS) == "ok"


def test_crash_after_brief_running_fails():
    watch = RolloutWatch("new")
    assert watch.update("new", "Running", 0) == "waiting"
    results = [watch.update("new", "CrashLoop", 10 + i) for i in range(FAILED_POLLS)]
    assert results[-1] == "failed"
    assert set(results[:-1]) == {"waiting"}


def test_a_single_failed_poll_is_not_enough():
    watch = RolloutWatch("new")
    assert watch.update("new", "CrashLoop", 0) == "waiting"
    assert watch.update("new", "Running", 10) == "waiting"
    assert watch.failed_polls == 0
