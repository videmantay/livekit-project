# Cloud Run gatekeeper

Checks invite codes, records consent, and issues short-lived LiveKit tokens. This is the only service with access to Firestore.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/invites/verify` | Checks a code without using a session, and returns the current terms in the requested `language` if it's offered, else English, plus the offered `languages` (ADR-15, ADR-20) |
| `POST` | `/sessions` | Records consent and its `terms_language`, uses one session, returns a LiveKit token. 503 with `Retry-After` under contention, or while `MAX_CONCURRENT_CALLS` calls are live, using no session |
| `GET` | `/health` | Health check |
| `GET` | `/admin/facts` | Working facts and every published version (admin sign-in) |
| `POST` | `/admin/facts` | Adds a draft fact (admin sign-in) |
| `PUT` | `/admin/facts/{id}` | Edits a fact; it stays a draft until published (admin sign-in) |
| `DELETE` | `/admin/facts/{id}` | Removes a fact from the working set (admin sign-in) |
| `POST` | `/admin/facts/publish` | Publishes the working set as the next numbered version (admin sign-in) |
| `POST` | `/admin/facts/rollback` | Publishes an earlier version as a new one and discards drafts (admin sign-in) |
| `GET` | `/admin/conversations` | The 100 newest sessions, each with invite label, summary, declined questions, transcript and contact details (admin sign-in) |
| `DELETE` | `/admin/conversations/{id}` | Deletes one session with its transcript, summary and contact details. The invite stays (admin sign-in) |
| `GET` | `/admin/invites` | Invites, newest first, by label. Never codes (admin sign-in) |
| `POST` | `/admin/invites` | Creates an invite from `label`, `sessionLimit` and `expiresInDays`. The code is in this response only (admin sign-in) |
| `POST` | `/admin/invites/{id}/revoke` | Stops a code working at once (admin sign-in) |
| `GET` | `/internal/facts` | The live published version, never drafts (signed by the agent) |
| `POST` | `/internal/sessions/{id}/transcript` | One batch of turns. `final: true` ends the call and writes the summary. 409 for a batch number already stored, or after the call ended (signed by the agent) |
| `POST` | `/internal/sessions/{id}/release` | The call ended before the visitor heard anything: gives the session back to the invite and ends the call, once per session (signed by the agent) |
| `POST` | `/webhooks/livekit` | LiveKit's `room_finished`, which ends and summarizes a call the agent didn't (signed by LiveKit) |

Admin routes need `Authorization: Bearer <Google ID token>` for `ADMIN_EMAIL`. Internal routes need the agent's HMAC signature, made with `AGENT_SIGNING_SECRET` (see `app/agent_auth.py`). The webhook needs LiveKit's signature, made with the project's API key and secret.

## Transcript batches

The agent numbers its batches from 0 and sends each one once:

```json
{"batch": 0, "turns": [{"speaker": "visitor", "text": "...", "violation": false}], "facts_version": 3, "final": false}
```

A batch number is stored once, so a replayed or retried request gets 409 and writes nothing. An agent that gets 409 on a retry can drop the batch. Batches after the call has ended are refused, so send everything before `final: true`.

## Summaries and notifications

When a call ends, Gemini writes the summary and lists the declined questions, through Vertex AI with the service's own identity and no tools (ADR-9). The transcript is treated as untrusted input. If the model fails, the call stays saved with `summaryStatus: "failed"`. Then an email with only a link goes to `ADMIN_EMAIL` over SMTP, if `SMTP_HOST` is set.

## Run locally

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## Create an invite

The code is shown once and only its hash is stored. Invites can also be created and revoked on the admin Access codes page.

```bash
uv run python -m app.create_invite --label "Acme recruiter" --expires-days 14
```

## Import the seed facts

A one-time import of the profile's `facts.yaml`: `PROFILE_DIR` if set, else `profile/`, else the fake sample in `profile.example/`. Pass a path to import another file. Only `reviewed: true` entries are imported, and the rest are listed. It refuses to run once any facts exist.

```bash
uv run python -m app.import_facts --publish
```

## Test

Tests run against the Firestore emulator, which needs Java. Run this from `firebase/`:

```bash
firebase emulators:exec --only firestore --project demo-portfolio "cd ../cloud-run && uv run pytest"
```

## Deploy

`deploy.sh` builds the `Dockerfile` with Cloud Build and deploys it to Cloud Run. Run the commands in Git Bash, with `PROJECT` set to the Firebase project ID.

### One-time setup

Turn on the APIs, and create a service account that can reach only Firestore and Vertex AI:

```bash
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com

gcloud iam service-accounts create gatekeeper
SA=gatekeeper@$PROJECT.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/datastore.user
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/aiplatform.user
```

Store the secrets in Secret Manager. `read -s` keeps each value out of the shell history. `agent-signing-secret` must be the same value the agent uses.

```bash
for name in livekit-api-secret agent-signing-secret smtp-password admin-email; do
  read -rsp "$name: " v; echo
  printf '%s' "$v" | gcloud secrets create $name --data-file=-
  gcloud secrets add-iam-policy-binding $name --member=serviceAccount:$SA \
    --role=roles/secretmanager.secretAccessor
done
```

To change a secret later, run `printf '%s' "$v" | gcloud secrets versions add <name> --data-file=-` and deploy again.

### Production config

Create `.env.production.yaml` here. It's gitignored and blocked by the pre-commit hook, because it holds the legal name and contact email (ADR-14). It takes the non-secret keys from `.env.example`:

```yaml
LIVEKIT_URL: wss://your-project.livekit.cloud
LIVEKIT_API_KEY: ...
LIVEKIT_AGENT_NAME: portfolio-twin
FIREBASE_PROJECT_ID: ...
ALLOWED_ORIGINS: https://lee.videmantay.net
ADMIN_URL: https://lee.videmantay.net/admin
OWNER_NAME: ...
TERMS_LEGAL_NAME: ...
TERMS_CONTACT_EMAIL: ...
GEMINI_MODEL: gemini-3.5-flash
VERTEX_LOCATION: global
SMTP_HOST: ...
SMTP_PORT: "587"
SMTP_USERNAME: ...
NOTIFY_FROM: ...
```

Leave the secrets and `GOOGLE_APPLICATION_CREDENTIALS` out of this file. Cloud Run uses the service account, and `deploy.sh` refuses to deploy if the file contains any of them.

### Deploy

```bash
bash deploy.sh
```

The defaults are the `gatekeeper` service in `us-central1`, with at most 2 instances. Override them with `REGION`, `SERVICE`, `SERVICE_ACCOUNT` or `MAX_INSTANCES`. The script ends by calling `/health`.

`.gcloudignore` keeps `.env`, tests and the virtualenv out of the upload, and the image copies only `app/`.

After the first deploy, put the service URL into the frontend's API URL and the agent's Cloud Run URL, and point LiveKit Cloud's webhook at `<url>/webhooks/livekit`.
