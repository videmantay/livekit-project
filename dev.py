# /// script
# requires-python = ">=3.12"
# ///
"""Runs the whole project locally, in one terminal. Ctrl+C stops everything.

    uv run dev.py              # emulator, cloud-run, agent and frontend
    uv run dev.py --no-agent   # skip the agent, which spends Tavus, ElevenLabs and Gemini credit

What runs where:
- Firestore emulator (localhost:8085). Starts empty each run, then gets the reviewed facts
  from livekit/facts/lee.yaml and one local invite code. Real Firestore is never touched.
- cloud-run (localhost:8000), pointed at the emulator.
- livekit agent in dev mode. It runs on this machine but registers with the LiveKit Cloud
  project in livekit/.env, because Tavus has to reach the room from the internet.
  cloud-run's tokens dispatch it to each visitor's room, as in production.
- firebase frontend (localhost:5173), pointed at local cloud-run.

The agent and cloud-run get a fresh shared signing secret each run, so neither .env needs one.
"""

import _thread
import argparse
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WINDOWS = os.name == "nt"

EMULATOR_PORT = 8085  # Matches firebase/firebase.json.
API_PORT = 8000
API_URL = f"http://localhost:{API_PORT}"
FRONTEND_URL = "http://localhost:5173"

# Names only. Values are never printed.
REQUIRED = {
    "cloud-run/.env": [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "TERMS_LEGAL_NAME",
        "TERMS_CONTACT_EMAIL",
        "ADMIN_EMAIL",
    ],
    "livekit/.env": [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "TAVUS_API_KEY",
        "TAVUS_FACE_ID",
        "ELEVEN_API_KEY",
        "ELEVENLABS_VOICE_ID",
        "GOOGLE_API_KEY",
    ],
}

COLORS = {"emulator": "33", "cloud-run": "36", "agent": "35", "frontend": "32", "dev": "1"}
print_lock = threading.Lock()


def say(name: str, line: str) -> None:
    with print_lock:
        print(f"\033[{COLORS.get(name, '0')}m[{name:>9}]\033[0m {line}", flush=True)


def child_env(extra: dict[str, str]) -> dict[str, str]:
    env = {**os.environ, **extra, "PYTHONUNBUFFERED": "1", "FORCE_COLOR": "1"}
    # `uv run dev.py` sets this for the script; each service uses its own .venv.
    env.pop("VIRTUAL_ENV", None)
    return env


def fail(message: str) -> None:
    say("dev", f"\033[31m{message}\033[0m")
    sys.exit(1)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def preflight(args: argparse.Namespace) -> dict[str, str]:
    tools = ["uv", "pnpm"]
    if not args.no_emulator:
        tools += ["firebase", "java"]
    missing_tools = [t for t in tools if not _which(t)]
    if missing_tools:
        fail(f"Not on PATH: {', '.join(missing_tools)}")

    problems = []
    for rel, keys in REQUIRED.items():
        if rel.startswith("livekit") and args.no_agent:
            continue
        path = ROOT / rel
        if not path.exists():
            problems.append(f"{rel} is missing. Copy it from {rel}.example and fill it in.")
            continue
        env = {**read_env(path), **os.environ}  # Values set in the shell win, as in the services.
        empty = [k for k in keys if not env.get(k)]
        if empty:
            problems.append(f"{rel} needs: {', '.join(empty)}")
    if args.no_emulator and not ({**read_env(ROOT / "cloud-run/.env"), **os.environ}).get("FIREBASE_PROJECT_ID"):
        problems.append("cloud-run/.env needs FIREBASE_PROJECT_ID to use real Firestore.")

    cloud = {**read_env(ROOT / "cloud-run/.env"), **os.environ}
    agent = {**read_env(ROOT / "livekit/.env"), **os.environ}
    if not args.no_agent:
        if cloud.get("LIVEKIT_URL") != agent.get("LIVEKIT_URL"):
            problems.append("LIVEKIT_URL differs between cloud-run/.env and livekit/.env.")
        name_c = cloud.get("LIVEKIT_AGENT_NAME", "portfolio-twin")
        name_a = agent.get("LIVEKIT_AGENT_NAME", "portfolio-twin")
        if name_c != name_a:
            problems.append("LIVEKIT_AGENT_NAME differs, so cloud-run would dispatch to nothing.")
    if problems:
        fail("Can't start:\n  " + "\n  ".join(problems))

    for port in (API_PORT, 5173) + (() if args.no_emulator else (EMULATOR_PORT,)):
        if _port_open(port):
            fail(f"Port {port} is already in use. Stop whatever is running there first.")
    return cloud


def _which(tool: str) -> bool:
    from shutil import which

    return which(tool) is not None


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


class Procs:
    def __init__(self) -> None:
        self.running: list[tuple[str, subprocess.Popen]] = []
        self.stopping = False

    def start(self, name: str, cmd: str, cwd: str, env: dict[str, str]) -> subprocess.Popen:
        say("dev", f"starting {name}: {cmd}")
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT / cwd,
            env=child_env(env),
            shell=True,  # pnpm and firebase are .cmd shims on Windows.
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            # Own process group, so Ctrl+C reaches us once and we stop each tree ourselves.
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0,
            start_new_session=not WINDOWS,
        )
        self.running.append((name, proc))
        threading.Thread(target=self._pump, args=(name, proc), daemon=True).start()
        return proc

    def _pump(self, name: str, proc: subprocess.Popen) -> None:
        assert proc.stdout
        for line in proc.stdout:
            say(name, line.rstrip())
        code = proc.wait()
        if not self.stopping:
            say("dev", f"\033[31m{name} exited with {code}. Stopping everything.\033[0m")
            _thread.interrupt_main()

    def stop(self) -> None:
        self.stopping = True
        for name, proc in reversed(self.running):
            if proc.poll() is not None:
                continue
            say("dev", f"stopping {name}")
            if WINDOWS:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    capture_output=True,
                )
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        for _, proc in self.running:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def wait_for(check, what: str, procs: Procs, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        if any(p.poll() is not None for _, p in procs.running):
            raise KeyboardInterrupt  # The pump thread already said which one died.
        time.sleep(0.5)
    say("dev", f"\033[31m{what} didn't come up within {timeout:.0f}s.\033[0m")
    raise KeyboardInterrupt


def api_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{API_URL}/health", timeout=1) as r:
            return r.status == 200
    except OSError:
        return False


def seed(env: dict[str, str]) -> None:
    """Fresh emulator, so: the reviewed facts, published, and one invite for trying the flow."""
    full_env = child_env(env)
    run = lambda cmd: subprocess.run(cmd, cwd=ROOT / "cloud-run", env=full_env, shell=True)  # noqa: E731
    if run("uv run python -m app.import_facts ../livekit/facts/lee.yaml --publish").returncode:
        fail("Importing the seed facts into the emulator failed.")
    if run('uv run python -m app.create_invite --label "local dev" --max-sessions 20').returncode:
        fail("Creating the local invite failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-agent", action="store_true", help="don't start the livekit agent")
    parser.add_argument(
        "--no-emulator",
        action="store_true",
        help="use the real Firestore in cloud-run/.env instead of the emulator (no seeding)",
    )
    args = parser.parse_args()
    if WINDOWS:
        os.system("")  # Turns on ANSI colours in the Windows console.
    # Child output can contain any character, and the Windows console default can't print all.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # Being closed or killed stops the services too, the same as Ctrl+C.
    for sig in ("SIGTERM", "SIGBREAK", "SIGHUP"):
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), lambda *_: _thread.interrupt_main())

    cloud = preflight(args)
    project = cloud.get("FIREBASE_PROJECT_ID") or "demo-portfolio"
    signing_secret = secrets.token_urlsafe(32)

    api_env = {
        "AGENT_SIGNING_SECRET": signing_secret,
        "ALLOWED_ORIGINS": FRONTEND_URL,
        "FIREBASE_PROJECT_ID": project,
    }
    if not args.no_emulator:
        # The Firestore client sees this and talks to the emulator with no credentials.
        api_env["FIRESTORE_EMULATOR_HOST"] = f"localhost:{EMULATOR_PORT}"

    procs = Procs()
    try:
        if not args.no_emulator:
            procs.start(
                "emulator",
                f"firebase emulators:start --only firestore --project {project}",
                "firebase",
                {},
            )
            wait_for(lambda: _port_open(EMULATOR_PORT), "The Firestore emulator", procs)
            seed(api_env)

        procs.start("cloud-run", f"uv run uvicorn app.main:app --reload --port {API_PORT}", "cloud-run", api_env)
        wait_for(api_healthy, "cloud-run", procs)

        if not args.no_agent:
            procs.start(
                "agent",
                "uv run agent.py dev",
                "livekit",
                {"CLOUD_RUN_URL": API_URL, "AGENT_SIGNING_SECRET": signing_secret},
            )

        procs.start("frontend", "pnpm dev", "firebase", {"VITE_API_URL": API_URL})

        say("dev", f"\033[1mReady. Frontend {FRONTEND_URL}, API {API_URL}. Ctrl+C stops everything.\033[0m")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        procs.stop()


if __name__ == "__main__":
    main()
