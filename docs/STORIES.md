# User stories

The agreed security measures in [ADRS.md](ADRS.md) take priority here. The design file sets styling and a loose workflow only.

Status of each acceptance check:

- ✅ Passes in `cloud-run/tests/` against the Firestore emulator
- ⚠️ Built, but unreliable or only partly checked
- ⬜ Not built yet

Last checked 2026-11-01. 23 of 24 tests pass every time, and the other fails intermittently (see I9). Nothing has run against a real LiveKit project or a deployed service yet.

## Uninvited visitor

Someone with no code, or a bad one, including anyone probing the service.

### U1. I'm told a code doesn't work, and nothing more

As an uninvited visitor, when I enter a code that doesn't work, I see one generic message, so nobody can learn whether a code ever existed.

- ✅ Wrong, expired, revoked and used-up codes get an identical 403
- ⬜ The gate screen shows that message and doesn't uppercase or reformat what was typed

### U2. Guessing codes gets me nowhere

As the site owner, I want guessing to be impractical, so codes can't be found by brute force.

- ✅ Codes are 144-bit random values, and only their hash is stored
- ⚠️ The limiter blocks and recovers in a unit test, but the 429 isn't tested through the endpoints
- ⚠️ The limit counts per Cloud Run instance, and the client IP logic is unverified on real Cloud Run
- ⬜ The gate screen shows a separate "try again shortly" message on a 429

### U3. I can't reach any data or start a call

As the site owner, I want someone without a valid invite to be stopped at every layer, so they can't reach stored data or run up vendor costs.

- ✅ Browser-style reads and writes to Firestore are refused
- ✅ API docs and the OpenAPI schema are off
- ✅ Only configured origins pass CORS
- ✅ No token is issued without a valid invite and recorded consent
- ⬜ Confirmed on real LiveKit: the agent joins only rooms created through `cloud-run`

### U4. I know how to ask for an invite

As an uninvited visitor, I can see how to reach Lee, so a missing code isn't a dead end.

- ⬜ The gate shows a static LinkedIn link, and nothing about me is stored (ADR-16)

### U5. What I can read without an invite

As an uninvited visitor, I can see only what Lee considers public.

- ⚠️ `GET /terms` needs no invite today, so it exposes the legal name and contact email
- ⬜ The terms are returned only after a valid code, and `GET /terms` is removed (ADR-15)

## Invited visitor

A recruiter or employer who was sent a code.

### I1. I can check my code without using it up

As an invited visitor, I can enter my code and move on to the terms without spending a session.

- ✅ Verifying a code leaves `sessions_used` unchanged
- ⬜ Gate screen
- ⬜ A valid code returns the terms (ADR-15)

### I2. I agree to clear terms before anything starts

As an invited visitor, I read the terms and tick an unticked box before my microphone is requested, so I know what happens to my conversation.

- ✅ The terms say it's an AI avatar, that nothing it says binds Lee, and cover storage, vendors, retention and deletion
- ✅ No token without `terms_accepted: true`, and malformed consent uses no session
- ✅ Terms version and acceptance time are saved with the session
- ⬜ Terms screen, with the box unticked by default and the mic requested only afterwards
- ⬜ Lawyer review of the terms text

### I3. If the terms change, I see the new ones

As an invited visitor whose page is out of date, I'm asked to review the current terms, so my consent always matches what's in force.

- ✅ An outdated version gets a 409 and uses no session
- ⬜ The frontend reloads the terms on a 409

### I4. I can leave my contact details if I want to

As an invited visitor, I can optionally give my name, email and company in a form, so Lee can reach me and the avatar never handles them.

- ✅ Contact details are optional, validated, and stored apart from the session
- ✅ No contact document is written when none is given
- ⬜ Contact form

### I5. I join a private, limited call

As an invited visitor, I join my own room, and my access covers nothing else.

- ✅ Each session gets its own room
- ✅ The token covers one room, the microphone only, no data publishing, no admin rights, and expires in 5 minutes
- ⬜ Call screen, connected to a real LiveKit project

### I6. I always know I'm talking to an AI

As an invited visitor, I'm reminded throughout that this isn't the real Lee, and that the conversation is being saved.

- ⬜ A permanent label on the video reads "AI avatar of Lee, not the real person" and can't be dismissed
- ⬜ The avatar says so in its greeting and answers honestly whenever asked
- ⬜ A visible "transcript being saved" indicator
- ⬜ Speaker labels read "Lee (AI)", never "Lee"

### I7. I can talk to the avatar and leave when I want

As an invited visitor, I can speak with the avatar about Lee's experience and end the call at any time.

- ⬜ Agent with Tavus, ElevenLabs and Gemini
- ⬜ Mute and End Session controls
- ⬜ The visitor sees the session length before starting, and a warning before it ends
- ⬜ The agent ends the call at `MAX_SESSION_MINUTES` (15). The browser can't extend it.

### I8. The avatar can't overstep

As an invited visitor and as Lee, we need the avatar to stay within public information and never commit Lee to anything.

- ⬜ The agent knows only the material Lee has marked public and verified
- ⬜ It sends offers, pay, start dates and availability to Lee directly
- ⬜ It has no database access, no tools that read data, and can't see other sessions
- ⬜ Prompt-extraction and commitment attempts are tested
- ⬜ It says Lee lacks a skill the fact file lists as a "no", such as Microsoft Server (ADR-19)
- ⬜ It declines general technical questions and anything the fact file doesn't cover, and points me to Lee
- ⬜ Security answers stay within Lee's written application-level notes
- ⬜ Grounding tests, including pushy follow-ups, block a deploy when they fail

### I9. My invite has a limit, and failures are handled

As an invited visitor, I know my invite covers a set number of sessions, and a problem gives me a clear next step.

- ✅ The session limit is enforced, and separate sessions get separate rooms
- ⚠️ **Known bug:** simultaneous redemptions can exhaust Firestore's retries and return a 500. The concurrency test failed on 3 of 8 runs. No run showed the limit exceeded, but failed runs stop before that check.
- ⬜ The start button blocks double clicks, which would otherwise spend two sessions
- ⬜ A declined mic or lost connection after starting explains what happened and how to reach Lee. Either one uses a session (ADR-4).

### I10. My data doesn't stay forever

As an invited visitor, my data is deleted automatically, and I can ask for it to be deleted sooner.

- ✅ Sessions and contacts get a `delete_at` 90 days out
- ⚠️ TTL is configured but not deployed, and the emulator doesn't run it, so nothing is being deleted yet
- ⬜ Transcripts and summaries get the same `delete_at`
- ⬜ The deletion request process exists (A7)

### I11. I get an honest picture of Lee's languages

As an invited visitor, I can see Lee's real language level, so the avatar's speech doesn't mislead me.

- ⬜ The avatar states Spanish as fluent and Portuguese as B2 (ADR-20)
- ⬜ The call screen shows a clip labelled "Lee's real voice, unedited"
- ⬜ Asked to speak Portuguese or translate, the avatar stays in English, gives the level and points to the clip
- ⬜ Spoken to in another language, the avatar replies in English
- ⬜ Portuguese speech is tested against the agent's speech recognition
- ⬜ Later: a Portuguese question can get a prepared answer, played word for word from Lee's recording
- ⬜ Later: before the first prepared answer, I hear that it's Lee's real voice, recorded in advance, and that Lee's conversational Portuguese is about B2
- ⬜ Later: a Portuguese question with no prepared answer gets an English reply, or Spanish if I asked for Spanish
- ⬜ The avatar never generates Portuguese

## Admin

Lee, the only admin.

### A1. I can create an invite

As the admin, I can create an invite with a label, a session limit and an expiry, and see the code once.

- ✅ The code is random, stored only as a hash, and can't be shown again
- ⚠️ The CLI exists, but the command itself has no test and hasn't run against real Firestore
- ⬜ Access codes page in `/admin`, showing labels and never codes

### A2. I can revoke an invite

As the admin, I can stop a code working immediately.

- ✅ A revoked code is refused
- ⚠️ Today this means editing the document in the Firebase console
- ⬜ Revoke action in `/admin`

### A3. Only I can get into admin

As the admin, I sign in with Google, and nobody else gets in.

- ⬜ `/admin` behind Google sign-in, limited to one account
- ⬜ `cloud-run` verifies the sign-in on every request, and the browser still never touches Firestore
- ⬜ Tests cover no token, an invalid token and the wrong account

### A4. Every conversation is saved reliably

As the admin, I get the transcript even if something fails mid-call.

- ⬜ The agent sends transcript turns to a signed internal `cloud-run` endpoint in batches
- ⬜ Text only, with no audio or video
- ⬜ A LiveKit `room_finished` webhook closes the session if the agent dies
- ⬜ Forged or replayed calls to both endpoints are refused

### A5. I get a tl;dr I can check

As the admin, I read a short summary of each conversation and can compare it with the transcript, because a visitor could try to steer it.

- ⬜ `cloud-run` writes the summary when the call ends
- ⬜ The summary step has no tools and treats the transcript as untrusted input
- ⬜ The summary links to its transcript
- ⬜ The summary lists the questions the avatar declined (ADR-19)

### A6. I can review conversations and contacts

As the admin, I can see who I invited, what they asked, and any contact details they left.

- ⬜ Conversations page with invite label, date, length, tl;dr and transcript
- ⬜ Contact details shown beside the session
- ⬜ A notification email containing only a link, with no contact details or conversation content

### A7. I can honour a deletion request

As the admin, I can delete one person's data when they ask.

- ⬜ Deletes the session, transcript, summary and contact details together
- ⬜ Documented steps for asking vendors to delete their copies, if they keep any

### A8. I control what the avatar knows

As the admin, I decide what the avatar can repeat, assuming a visitor can extract all of it.

- ⬜ The agent gets only entries I've published, never drafts (ADR-21)
- ⬜ Each entry gives a topic, level, what's verified and its limits, and skills I lack are listed too (ADR-19)
- ⬜ Facts page in `/admin` where I edit drafts and publish them, with no deploy (ADR-21)
- ⬜ Each publish is a numbered version, and I can roll back to an earlier one in one step
- ⬜ A published change reaches the next call, and each transcript records the version used
- ⬜ If `cloud-run` can't be reached, the agent uses the last version it fetched, and ends the call politely if it has none
- ⬜ Grounding tests run against the published facts before each deploy and nightly, and a failure notifies me

### A10. I can turn declined questions into facts

As the admin, I can add an answer for a question the avatar declined, so the next visitor gets it.

- ⬜ Each declined question in a summary has an "Add as fact" action (ADR-19, ADR-21)
- ⬜ It opens a draft with the question filled in, copying nothing about who asked

### A9. Secrets stay out of this public repo

As the admin, I can work in public without leaking keys.

- ⚠️ `.gitignore` and a pre-commit hook block secret files. The hook has no test and must be turned on in each clone.
- ⬜ Secret Manager on Cloud Run, and agent secrets on LiveKit Cloud
- ⬜ Logs are checked to contain no codes, tokens, transcripts or contact details
