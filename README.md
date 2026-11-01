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
