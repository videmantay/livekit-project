# Interactive portfolio

A portfolio with a voice and video twin avatar. Each top-level folder is one deploy target.

| Folder | Deploys to | Purpose |
|---|---|---|
| `cloud-run/` | Google Cloud Run | FastAPI gatekeeper: checks invite codes and issues LiveKit tokens |
| `livekit/` | LiveKit Cloud | Agent: Tavus avatar, ElevenLabs voice, Gemini |
| `firebase/` | Firebase Hosting | React frontend |

## Setup

This is a public repo. Turn on the secret-file guard once per clone:

```bash
git config core.hooksPath .githooks
```

Then create a local env file in each target and fill it in:

```bash
cp cloud-run/.env.example cloud-run/.env
```

```bash
cp livekit/.env.example livekit/.env
```

```bash
cp firebase/.env.example firebase/.env.local
```

Install dependencies with `uv sync` in `cloud-run/` and `livekit/`, and `pnpm install` in `firebase/`.

## Run everything locally

```bash
uv run dev.py               # Firestore emulator, cloud-run, agent and frontend
uv run dev.py --no-agent    # same, without the agent (it spends Tavus, ElevenLabs and Gemini credit)
uv run dev.py --no-emulator # real Firestore from cloud-run/.env, with no seeding
```

Output from every service appears in one terminal, and Ctrl+C stops them all. The Firestore emulator needs Java and starts empty each run. The script imports the reviewed facts and prints a fresh invite code for `/invite`.

The agent runs on your machine in dev mode, but registers with the LiveKit Cloud project in `livekit/.env`, because Tavus joins the room from the internet. Both `.env` files need the same `LIVEKIT_URL` and `LIVEKIT_AGENT_NAME`. If a deployed agent with the same name is also live, it can take the call instead. The script gives cloud-run and the agent a new shared `AGENT_SIGNING_SECRET` each run, so neither `.env` needs one locally.
