# Cloud Run gatekeeper

Checks invite codes, records consent, and issues short-lived LiveKit tokens. This is the only service with access to Firestore.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/invites/verify` | Checks a code without using a session, and returns the current terms (ADR-15) |
| `POST` | `/sessions` | Records consent, uses one session, returns a LiveKit token |
| `GET` | `/health` | Health check |
| `GET` | `/admin/facts` | Working facts and every published version (admin sign-in) |
| `POST` | `/admin/facts` | Adds a draft fact (admin sign-in) |
| `PUT` | `/admin/facts/{id}` | Edits a fact; it stays a draft until published (admin sign-in) |
| `DELETE` | `/admin/facts/{id}` | Removes a fact from the working set (admin sign-in) |
| `POST` | `/admin/facts/publish` | Publishes the working set as the next numbered version (admin sign-in) |
| `POST` | `/admin/facts/rollback` | Publishes an earlier version as a new one and discards drafts (admin sign-in) |
| `GET` | `/internal/facts` | The live published version, never drafts (signed by the agent) |

Admin routes need `Authorization: Bearer <Google ID token>` for `ADMIN_EMAIL`. Internal routes need the agent's HMAC signature, made with `AGENT_SIGNING_SECRET` (see `app/agent_auth.py`).

## Run locally

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## Create an invite

The code is shown once and only its hash is stored. To revoke an invite, set `revoked` to `true` on its document in the `invites` collection.

```bash
uv run python -m app.create_invite --label "Acme recruiter" --expires-days 14
```

## Import the seed facts

A one-time import of `livekit/facts/lee.yaml`. Only `reviewed: true` entries are imported, and the rest are listed. It refuses to run once any facts exist.

```bash
uv run python -m app.import_facts ../livekit/facts/lee.yaml --publish
```

## Test

Tests run against the Firestore emulator, which needs Java. Run this from `firebase/`:

```bash
firebase emulators:exec --only firestore --project demo-portfolio "cd ../cloud-run && uv run pytest"
```
