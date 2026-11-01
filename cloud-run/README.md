# Cloud Run gatekeeper

Checks invite codes, records consent, and issues short-lived LiveKit tokens. This is the only service with access to Firestore.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/terms` | Current terms text and version |
| `POST` | `/invites/verify` | Checks a code without using a session |
| `POST` | `/sessions` | Records consent, uses one session, returns a LiveKit token |
| `GET` | `/health` | Health check |

## Run locally

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## Create an invite

The code is shown once and only its hash is stored. To revoke an invite, set `revoked` to `true` on its document in the `invites` collection.

```bash
uv run python -m app.create_invite --label "Acme recruiter" --expires-days 14
```

## Test

Tests run against the Firestore emulator, which needs Java. Run this from `firebase/`:

```bash
firebase emulators:exec --only firestore --project demo-portfolio "cd ../cloud-run && uv run pytest"
```
