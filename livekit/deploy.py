"""Safe deploy to LiveKit Cloud: check, deploy, watch, and roll back on failure.

    uv run python deploy.py

1. Lint and unit tests must pass.
2. Every secret the agent needs at startup must exist in LiveKit Cloud. A required setting added
   in code without its secret crash-loops the agent (2026-11-18, ELEVENLABS_SPANISH_VOICE_ID).
3. The version live now is recorded as the known-good one.
4. `lk agent deploy` ships the new version.
5. The rollout is watched until the new version stays Running for STABLE_SECONDS. If it
   crash-loops, errors, or never settles within ROLLOUT_TIMEOUT_SECONDS, the script rolls back to
   the known-good version and exits non-zero.

Only secret names are read from LiveKit Cloud, never values, and nothing here logs them (ADR-14).
"""

import json
import shutil
import subprocess
import sys
import time

from config import AgentSettings

# Read by the SDK plugins straight from the environment, so they aren't AgentSettings fields.
PLUGIN_SECRETS = ("ELEVEN_API_KEY", "GOOGLE_API_KEY")
# Production fetches facts from and sends transcripts to cloud-run (ADR-2, ADR-9). Without them
# the agent starts but falls back to the local seed file, which production must never do.
PRODUCTION_SECRETS = ("CLOUD_RUN_URL", "AGENT_SIGNING_SECRET")

POLL_SECONDS = 10
# A crash on import shows Running for a few seconds first, so one Running poll proves nothing.
STABLE_SECONDS = 60
# Statuses seen this many polls in a row, after the new version is live, fail the rollout.
FAILED_POLLS = 3
FAILED_STATUSES = {"CrashLoop", "Error", "Failed"}
ROLLOUT_TIMEOUT_SECONDS = 6 * 60


def required_secrets() -> set[str]:
    """Every environment variable the agent can't start or run in production without."""
    fields = {
        name.upper() for name, field in AgentSettings.model_fields.items() if field.is_required()
    }
    return fields | set(PLUGIN_SECRETS) | set(PRODUCTION_SECRETS)


def missing_secrets(required: set[str], present: set[str]) -> list[str]:
    return sorted(required - present)


def current_version(versions: dict) -> str | None:
    for version in versions.get("versions", []):
        if version.get("current"):
            return version["version"]
    return None


def deployment_state(status: dict) -> tuple[str | None, str | None]:
    """The (version, status) of the agent's deployment, or Nones when there is none yet."""
    agents = status.get("agents") or [{}]
    deployments = agents[0].get("agentDeployments") or [{}]
    return deployments[0].get("version"), deployments[0].get("status")


class RolloutWatch:
    """Decides, poll by poll, whether a new version has settled or failed.

    Statuses from before the new version is live are ignored: LiveKit Cloud reports the
    previous version's state, sometimes stale, until the rollout reaches the new one.
    """

    def __init__(self, new_version: str):
        self.new_version = new_version
        self.running_since: float | None = None
        self.failed_polls = 0

    def update(self, version: str | None, status: str | None, now: float) -> str:
        """Returns "ok", "failed" or "waiting"."""
        if version != self.new_version:
            return "waiting"
        if status in FAILED_STATUSES:
            self.running_since = None
            self.failed_polls += 1
            return "failed" if self.failed_polls >= FAILED_POLLS else "waiting"
        self.failed_polls = 0
        if status != "Running":
            self.running_since = None
            return "waiting"
        if self.running_since is None:
            self.running_since = now
        return "ok" if now - self.running_since >= STABLE_SECONDS else "waiting"


def lk(*args: str, capture: bool = True) -> str:
    exe = shutil.which("lk")
    if exe is None:
        sys.exit("The LiveKit CLI `lk` isn't on PATH.")
    result = subprocess.run(
        [exe, "agent", *args],
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        if capture:
            # stderr carries the CLI's own messages, never secret values.
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"lk agent {args[0]} failed (exit {result.returncode})")
    return result.stdout if capture else ""


def lk_json(*args: str) -> dict:
    return json.loads(lk(*args, "--json"))


def run_checks() -> None:
    for step in (["ruff", "check", "."], ["pytest", "-q"]):
        print(f"→ {' '.join(step)}")
        if subprocess.run(["uv", "run", "--frozen", *step], check=False).returncode != 0:
            sys.exit(f"✗ {step[0]} failed. Nothing was deployed.")


def check_secrets() -> None:
    present = {secret["name"] for secret in lk_json("secrets").get("secrets", [])}
    missing = missing_secrets(required_secrets(), present)
    if missing:
        names = ", ".join(missing)
        sys.exit(
            f"✗ Missing LiveKit Cloud secrets: {names}\n"
            f"  Add them with: lk agent update-secrets --secrets \"NAME=value\"\n"
            f"  Nothing was deployed."
        )
    print("✓ All required secrets are set")


def rollback(version: str) -> None:
    print(f"↩ Rolling back to {version}")
    lk("rollback", "--version", version, "-y", capture=False)


def watch_rollout(new_version: str) -> bool:
    watch = RolloutWatch(new_version)
    deadline = time.monotonic() + ROLLOUT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            version, status = deployment_state(lk_json("status"))
        except (RuntimeError, ValueError) as error:
            print(f"  status check failed, retrying: {error}")
        else:
            print(f"  {version}: {status}")
            match watch.update(version, status, time.monotonic()):
                case "ok":
                    return True
                case "failed":
                    return False
        time.sleep(POLL_SECONDS)
    print("  timed out waiting for the new version to settle")
    return False


def main() -> None:
    run_checks()
    check_secrets()

    stable = current_version(lk_json("versions"))
    print(f"✓ Known-good version: {stable or 'none (first deploy)'}")

    print("→ lk agent deploy")
    lk("deploy", "-y", capture=False)

    new_version = current_version(lk_json("versions"))
    if new_version is None or new_version == stable:
        sys.exit("✗ The deploy didn't create a new current version. Check `lk agent versions`.")
    print(f"→ Watching {new_version} roll out")

    if watch_rollout(new_version):
        print(f"✓ {new_version} is live and stable")
        return

    print(f"✗ {new_version} failed to start. Check: lk agent logs", file=sys.stderr)
    if stable:
        rollback(stable)
        sys.exit(f"✗ Rolled back to {stable}. Production is on the known-good version.")
    sys.exit("✗ No earlier version to roll back to.")


if __name__ == "__main__":
    main()
