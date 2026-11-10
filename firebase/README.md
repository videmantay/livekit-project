# firebase

The visitor and admin frontend: React 19, TypeScript, Vite, Tailwind v4 and shadcn/ui, served from Firebase Hosting. This folder also holds the Firestore rules and TTL config. See [CLAUDE.md](CLAUDE.md) for commands and rules.

## Pages

| Path | What it is |
|---|---|
| `/` | Public portfolio: projects, experience and education, with a link to `/invite`. Content is in `src/landing/content.ts`. |
| `/invite` | Visitor flow: access code, then terms, then optional contact details, then the call |
| `/admin` | Lee's admin: conversations, access codes and facts, behind Google sign-in |

## Preview mode

The frontend isn't connected to `cloud-run` yet. Every request goes to an in-memory mock (`src/lib/api.ts` and `src/lib/admin-api.ts`) with sample data, and a banner says so. Admin sign-in is a button that lets you straight in.

At the `/invite` gate, any code works except these, which act out the failure states:

| Code | What happens |
|---|---|
| `bad` | 403: the generic "code doesn't work" message |
| `slow` | 429: the "wait a minute" message |
| `stale` | 409 on start: the terms reload and the box is unticked again |
| `used` | Passes the gate, then 403 on start: back to the gate |
| `drop` | The call starts, then the connection is lost after 5 seconds |

Refusing the microphone prompt shows the mic failure screen.

## Setup

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```
