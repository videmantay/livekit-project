# Architecture decisions

**Accepted** decisions are agreed. Some aren't built yet, which is noted in their status.

| # | Decision | Status |
|---|---|---|
| 1 | One folder per deploy target | Accepted |
| 2 | Only `cloud-run` touches stored data | Accepted |
| 3 | Long random invite codes, stored as hashes | Accepted |
| 4 | Consent comes before the mic and the token | Accepted |
| 5 | Visitor tokens are mic-only, for one room | Accepted |
| 6 | Text-only storage with 90-day deletion | Accepted |
| 7 | Everything the agent knows is treated as public | Accepted |
| 8 | Contact details come through a form | Accepted |
| 9 | Transcripts go through `cloud-run`; summaries have no tools | Accepted |
| 10 | Admin uses Google sign-in, verified by `cloud-run` | Accepted |
| 11 | Disclose the AI in the UI and in speech | Accepted |
| 12 | Security decisions outrank the design file | Accepted |
| 13 | shadcn/ui and Tailwind v4, dark theme only | Accepted |
| 14 | Public repo secret handling | Accepted |
| 15 | Show the terms only after a valid code | Accepted |
| 16 | No request-access form | Accepted |
| 17 | First release scope | Accepted |
| 18 | Tag releases on `main`, one version for the repo | Accepted |
| 19 | The agent answers only from verified facts | Accepted |
| 20 | Show language levels with real proof, not AI speech | Accepted |

## ADR-1: One folder per deploy target

**Status:** Accepted

**Context:** The system has three parts that deploy separately.

**Decision:** Keep `cloud-run/` (FastAPI gatekeeper), `livekit/` (agent on LiveKit Cloud) and `firebase/` (React on Firebase Hosting, plus Firestore config) at the top level.

**Consequences:** The targets depend on each other through agent names and token format, so they're released together (ADR-18).

## ADR-2: Only `cloud-run` touches stored data

**Status:** Accepted

**Context:** The main ways to leak data are a browser reaching the database, or a visitor manipulating the agent into reading it.

**Decision:** Firestore rules deny all client access, and `cloud-run` uses its service identity. The agent has no Firebase credentials and no tools that read data. It sends transcripts to a signed internal endpoint.

**Consequences:** Admin pages go through `cloud-run` too. Sessions can't leak into each other through the agent, because it never sees another session.

## ADR-3: Long random invite codes, stored as hashes

**Status:** Accepted

**Context:** Codes are the only gate to a paid service. The design shows a short uppercase `XXXX-XXXX-XXXX` format, which conflicts with the agreed long random codes.

**Decision:** Codes stay as generated: 144 bits of randomness, case-sensitive, and stored only as a SHA-256 hash. Each invite has a label, a session limit (default 2), an expiry (default 14 days) and a revoked flag. Every failure returns the same response. Requests are rate limited per client.

The UI adapts to the code, which replaces last session's suggestion to shorten it. The gate must not uppercase input, and it should trim pasted whitespace.

**Consequences:** Codes are meant to be pasted, not typed. Lost codes can't be recovered, so Lee issues a new one. Rate limiting is per instance, so max-instances must stay low.

## ADR-4: Consent comes before the mic and the token

**Status:** Accepted

**Context:** The visitor must agree before any data is collected, and Lee needs proof of what they agreed to.

**Decision:** The order is valid code, then terms with an unticked box, then `POST /sessions`, then the mic. `cloud-run` records consent in the same transaction that uses a session. The terms version is a hash of the text, so any wording change requires fresh consent.

**Consequences:** A session is spent before the mic is requested. A declined mic, a failed connection or a page refresh each use one. This is accepted to keep the agreed order, and the default limit of 2 leaves room for one failure. Lee can issue a new code.

## ADR-5: Visitor tokens are mic-only, for one room

**Status:** Accepted

**Context:** A token sits in the browser, so the visitor controls it.

**Decision:** Each token covers one randomly named room, allows only microphone publishing, allows no data publishing, has no admin grants and expires in 5 minutes. The agent joins through explicit dispatch, only in rooms created by `cloud-run`.

Visitor camera is out, because the agent doesn't need it and it adds privacy exposure. Typed questions are out for now, because they need data publishing.

**Consequences:** The browser can't enforce the session limit. The agent must end the call at `MAX_SESSION_MINUTES`, which stays at 15.

## ADR-6: Text-only storage with 90-day deletion

**Status:** Accepted

**Context:** Lee wants to review conversations, and visitors are told what's kept and for how long.

**Decision:** Store `invites`, `sessions`, `sessions/{id}/transcript` and `contacts`. Keep text only, with no audio or video. Contacts stay apart from transcripts. Everything about a visitor gets a `delete_at`, and Firestore TTL removes it. Deletion requests are honoured sooner.

**Consequences:** The 90-day promise isn't enforced until the TTL config is deployed. Summaries are stored on the session, so they go with it. Invites have no `delete_at` yet, and their labels can name a person.

## ADR-7: Everything the agent knows is treated as public

**Status:** Accepted

**Context:** A visitor can eventually get the agent to repeat whatever is in its prompt.

**Decision:** The agent gets only what Lee has marked both public and verified, which comes from the résumé and anything else Lee adds (ADR-19). Salary history, private contact details and notes on invitees stay out. It must not agree to offers, pay, start dates or availability, and sends those to Lee.

**Consequences:** Knowledge changes are reviewed before each agent deploy. Being on the résumé makes something public, but not automatically verified.

## ADR-8: Contact details come through a form

**Status:** Accepted

**Context:** Speech can be mistranscribed, and the agent shouldn't handle personal details.

**Decision:** An optional form sends contact details directly to `cloud-run`.

**Consequences:** Visitors may still say details aloud, which puts them in the transcript. The terms warn against sharing sensitive information.

## ADR-9: Transcripts go through `cloud-run`; summaries have no tools

**Status:** Accepted, not built

**Context:** A crash shouldn't lose a conversation, and transcripts are untrusted input that can try to steer the tl;dr.

**Decision:** The agent sends turns in batches during the call. `cloud-run` writes the summary at the end, and a LiveKit `room_finished` webhook is the fallback if the agent dies. The summary step has no tools, and each summary links to its transcript.

**Consequences:** `cloud-run` gains two authenticated endpoints, each of which needs signature tests.

## ADR-10: Admin uses Google sign-in, verified by `cloud-run`

**Status:** Accepted, not built

**Context:** Admin shows contact details and transcripts.

**Decision:** A private `/admin` page sits behind Google sign-in for one allowed account, and `cloud-run` verifies the sign-in on every request. Notification emails contain only a link. Pages show invite labels, never codes.

The first version covers Conversations and Access codes. Pipeline, tags, transcript search, an in-app knowledge base and email drafting are out of scope.

**Consequences:** The `firebase` web package is needed for sign-in only. `cloud-run` CORS must allow the `Authorization` header.

## ADR-11: Disclose the AI in the UI and in speech

**Status:** Accepted, not built

**Context:** Visitors must never think they're talking to the real Lee.

**Decision:** The video carries a permanent label that can't be dismissed. The avatar says it's an AI in its greeting and answers honestly when asked. The UI shows that the transcript is being saved and offers an End Session button. Speakers are labelled "Lee (AI)".

**Consequences:** Design wording such as "Lee is speaking" changes.

## ADR-12: Security decisions outrank the design file

**Status:** Accepted

**Context:** The design includes features that conflict with these decisions, such as a replay needing recordings, a camera tile, and a code shown in admin.

**Decision:** The design sets styling and a loose workflow. Where it conflicts with an agreed security measure, the security measure stands and the UI changes.

**Consequences:** A design feature is built only if it fits these decisions.

## ADR-13: shadcn/ui and Tailwind v4, dark theme only

**Status:** Accepted

**Context:** The design is a custom look that a styled component library would fight.

**Decision:** Use shadcn/ui on Radix, with Tailwind v4 tokens in `firebase/src/index.css`, and fonts installed as packages.

**Consequences:** LiveKit's components still need mapping to these tokens.

## ADR-14: Public repo secret handling

**Status:** Accepted

**Context:** The repo is public, and tags and history are too.

**Decision:** Only `.env.example` files are committed. `.gitignore` and a pre-commit hook block secret files. Production secrets live in Secret Manager and LiveKit Cloud secrets. Lee's legal name and contact email are set through config, not code. Logs never contain transcripts, contact details, codes or tokens.

**Consequences:** The hook must be enabled in each clone. A leaked secret must be rotated, because deleting it from history isn't enough.

## ADR-15: Show the terms only after a valid code

**Status:** Accepted, not built

**Context:** `GET /terms` is public, so anyone who finds the URL can read Lee's legal name and contact email. Only invited visitors need the terms.

**Decision:** Return the terms from `POST /invites/verify` and remove `GET /terms`. This puts them behind the same rate limit and gate.

**Alternative rejected:** Keeping them public is simpler and lets anyone read the terms in advance, but leaves the legal name one request away.

**Consequences:** One endpoint and its test change, and the frontend gets the terms from the verify response.

## ADR-16: No request-access form

**Status:** Accepted

**Context:** A public form would collect data from people who haven't agreed to any terms, and would need its own spam protection.

**Decision:** The gate shows a static LinkedIn link, and `cloud-run` stores nothing about uninvited visitors.

**Consequences:** Uninvited visitors reach Lee through LinkedIn only.

## ADR-17: First release scope

**Status:** Accepted

**Context:** Each extra feature adds consent text, access control or permissions.

**Decision:** The first release is English only, because each language needs its own reviewed consent text. It has no visitor recap page, because a recap needs its own access control and a mention in the terms. It has no shared-links panel, because that isn't needed to prove the flow.

**Consequences:** Spanish and Portuguese, the recap and shared links each get their own decision later. ADR-20 sets the limits for that language decision.

## ADR-18: Tag releases on `main`, one version for the repo

**Status:** Accepted

**Context:** Tags are only useful once they mark what's running.

**Decision:** Tag `v0.1.0` on `main` when the full flow works end to end: invite, consent, call and saved transcript. Use annotated tags and one version across all three targets. Move to `v1.0.0` when invites go to real employers.

**Consequences:** `dev` must merge to `main` before each release.

## ADR-19: The agent answers only from verified facts

**Status:** Accepted, not built

**Context:** Given only a résumé, the model confidently answered cybersecurity questions Lee couldn't answer. A résumé says what Lee has done, not what Lee hasn't, so the model fills the gaps from its own knowledge. Anything it says in Lee's voice sounds like Lee's expertise, and that oversells Lee to recruiters.

**Decision:** The agent's knowledge is a fact file that Lee reviews entry by entry. Each entry gives a topic, a level, what's verified and its limits. The file also lists skills Lee doesn't have, so a "no" is stated rather than guessed.

- Questions about Lee are answered only from the file.
- General technical questions aren't answered from the model's own knowledge, even when it knows the answer.
- Application-level security answers come from notes Lee wrote, so the model doesn't decide what counts as "application level".
- If something isn't covered, the agent says so plainly and points the visitor to Lee, without guessing or implying Lee knows it.
- The whole file sits in the prompt, with no retrieval, because a missed lookup is when the model would improvise.
- Grounding tests run before each agent deploy, and a failure blocks it. They include unit tests with LLM judges, and simulated recruiters who push on missing skills.
- Each call summary lists the questions the agent declined, so Lee can decide what to verify and add.

**Alternative rejected:** A second model checking each answer during the call adds delay to a voice conversation. Tests and transcript review come first, and this can be revisited if they miss too much.

**Consequences:** Hallucinations are reduced, not eliminated, so transcript review stays part of the design. The avatar will decline questions a recruiter might expect it to handle. Declined questions must be identifiable in the transcript for the summary step to list them.

## ADR-20: Show language levels with real proof, not AI speech

**Status:** Accepted, not built

**Context:** Lee's Spanish is fluent and Lee's Portuguese is about B2. Portuguese generated by the avatar would sound far better than B2 in a clone of Lee's voice, which misleads visitors. Making the AI add mistakes on purpose would be fake too. Lee still wants visitors to be able to hear real Portuguese.

**Decision:** The avatar never generates Portuguese. The fact file states each level, and the call screen shows a short, unscripted clip labelled "Lee's real voice, unedited". The clip is a static asset and collects nothing from visitors. The rollout has three stages:

1. **First release:** English only (ADR-17). If asked to speak Portuguese, the avatar stays in English, gives Lee's level and points to the clip. It replies in English to any language and doesn't translate on request.
2. **Next:** the avatar can answer a Portuguese question with one of 8–12 prepared answers, each recorded by Lee. The model only picks the answer, and code plays the recording word for word. The first one is preceded by a note that this is Lee's real voice, recorded in advance, and that Lee's conversational Portuguese is about B2. Any question without a matching answer gets an English reply.
3. **After that:** the avatar can speak Spanish when a visitor asks, because that matches Lee's real level, once the translated consent text is reviewed. A Portuguese question without a matching answer then gets a Spanish reply if the visitor has asked for Spanish.

**Alternative rejected:** Speaking Lee's written answers through the AI voice would use Lee's words, but the delivery would still sound better than B2.

**Consequences:** Lee has to record the clip, the answers and the note. Stage 2 depends on Portuguese speech recognition and on the Tavus avatar lip-syncing to recorded audio, and neither has been tested. Prepared answers sound smoother than spontaneous speech, so the note and the unscripted clip both stay. Recordings of Lee's voice are personal data that Lee chooses to publish, so they go through the knowledge review.
