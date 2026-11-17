# firebase

The visitor and admin frontend: React 19, TypeScript, Vite, Tailwind v4 and shadcn/ui, served from Firebase Hosting. This folder also holds the Firestore rules and TTL config. See [CLAUDE.md](CLAUDE.md) for commands and rules.

## Pages

| Path | What it is |
|---|---|
| `/` | Public portfolio: projects, experience and education, with a link to `/invite`. Content is in `src/landing/content.ts`. |
| `/invite` | Visitor flow: access code, then terms, then optional contact details, then the call |
| `/admin` | Lee's admin: conversations, access codes and facts, behind Google sign-in |

## Preview mode

Each area falls back to an in-memory mock with sample data when its config is missing, and a banner says so. The two switches are independent:

- `/invite` uses `cloud-run` when `VITE_API_URL` is set, else the mock in `src/lib/api.ts`.
- `/admin` uses `cloud-run` and real Google sign-in when the `VITE_FIREBASE_*` values are set, else the mock in `src/lib/admin-api.ts`, where sign-in is a button that lets you straight in. Admin pages are never part real and part mock.

Codes made on the mock admin page are never stored, so a real `/invite` page always refuses them.

At the `/invite` gate, any code works except these, which act out the failure states:

| Code | What happens |
|---|---|
| `bad` | 403: the generic "code doesn't work" message |
| `slow` | 429: the "wait a minute" message |
| `stale` | 409 on start: the terms reload and the box is unticked again |
| `used` | Passes the gate, then 403 on start: back to the gate |
| `busy` | 503 on start, then the automatic retry a second later gets through |
| `jammed` | 503 on every start: the "busy, no session was used" message |
| `drop` | The call starts, then the connection is lost after 5 seconds |

Refusing the microphone prompt shows the mic failure screen.

## Setup

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```
