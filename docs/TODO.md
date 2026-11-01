# TODO

Story numbers refer to [STORIES.md](STORIES.md), and ADR numbers to [ADRS.md](ADRS.md).

## Fix now

- [ ] Handle exhausted Firestore transaction retries in `POST /sessions`, so contention can't return a 500, and make the concurrency test reliable (I9)
- [ ] Return the terms from `POST /invites/verify`, remove `GET /terms`, and update the tests and `cloud-run/README.md` (ADR-15, U5)
- [ ] Decide what happens to invites after expiry. They have no `delete_at`, and labels can name a person, which sits badly with the 90-day promise (ADR-6).
- [ ] Add an endpoint-level test for the 429 response (U2)
- [ ] Add a test for the invite CLI (A1)
- [ ] Commit the style system, which is still uncommitted on `dev`

## Frontend

- [ ] Gate screen with no uppercasing, trimmed paste, separate 403 and 429 messages, and a LinkedIn link (U1, U2, U4)
- [ ] Terms screen with an unticked box (I2), reloading on a 409 (I3)
- [ ] Optional contact form (I4)
- [ ] Call screen with AI label, saved-transcript indicator, mute and End Session (I6, I7)
- [ ] Map LiveKit's components to the theme tokens
- [ ] Double-click guard, and mic and connection failure states (I9)
- [ ] Replace the temporary style sheet in `App.tsx`
- [ ] Replace the Vite template text in `firebase/README.md`

## Agent

- [ ] Build the agent in `livekit/` with explicit dispatch (I7)
- [ ] Prompt rules for AI disclosure and no commitments (I6, I8)
- [ ] Public knowledge file with résumé content (A8)
- [ ] End the call at `MAX_SESSION_MINUTES` (I7)
- [ ] Test prompt extraction and commitment attempts (I8)

## Transcripts and summaries

- [ ] Signed internal endpoint for transcript batches (A4)
- [ ] `room_finished` webhook (A4)
- [ ] Summary step with no tools (A5)
- [ ] `delete_at` on transcripts (I10)

## Admin

- [ ] Google sign-in, verified by `cloud-run` on every request (A3)
- [ ] Conversations page (A6)
- [ ] Access codes page: create and revoke (A1, A2)
- [ ] Delete one person's data (A7)
- [ ] Link-only notification email (A6)

## Before the first invite

- [ ] Create the LiveKit, Tavus, ElevenLabs and Firebase production setup
- [ ] Deploy with low max-instances, and Secret Manager for secrets (U2, A9)
- [ ] Set `ALLOWED_ORIGINS` to the production origin
- [ ] Confirm `client_ip` reads the right address on real Cloud Run (U2)
- [ ] Deploy Firestore rules and TTL, then confirm a test document is deleted (I10)
- [ ] Confirm the agent can't be started without `cloud-run` (U3)
- [ ] Check logs for codes, tokens, transcripts and contact details (A9)
- [ ] Check Gemini's data use, and retention at ElevenLabs and Tavus
- [ ] Check whether LiveKit Cloud or Tavus record by default, since the terms say no audio or video is saved
- [ ] Have a lawyer review the terms, including recording consent and AI disclosure rules
- [ ] Run one full call end to end, then tag `v0.1.0` on `main` (ADR-18)

## Later

- [ ] Spanish and Portuguese, with translated consent text
- [ ] Visitor recap page
- [ ] Shared links during the call
- [ ] Typed questions, which need the data permission
