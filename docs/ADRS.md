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
| 13 | shadcn/ui and Tailwind v4, one theme | Accepted |
| 14 | Public repo secret handling | Accepted |
| 15 | Show the terms only after a valid code | Accepted |
| 16 | No request-access form | Accepted |
| 17 | First release scope | Accepted |
| 18 | Tag releases on `main`, one version for the repo | Accepted |
| 19 | The agent answers only from verified facts | Accepted |
| 20 | Show language levels with real proof, not AI speech | Accepted |
| 21 | Facts are edited in admin and fetched at call start | Accepted |
| 22 | The portfolio page is in English, Spanish and Portuguese | Accepted |
| 23 | The owner's profile is data, not code | Accepted, partly built |
| 24 | Speech-to-text is AssemblyAI through LiveKit Inference | Accepted |

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

**Invite links (added 2026-11-17):** Lee sends a link, `/invite#invite=<code>`, with the code as a fallback in the same message. The code goes only in the URL fragment, never the query string, because browsers don't send the fragment to a server. That keeps it out of Hosting logs and the Referer header (ADR-14). The page reads the code once, then removes it from the address bar. Opening a link only verifies the code, which uses no session (I1), so link-preview bots can't spend one. The terms and consent still come first (ADR-4, ADR-15). The site sends `Referrer-Policy: no-referrer`. A bad link gets the same generic message as a bad code (U1), and the paste box stays.

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

**Consequences:** The browser can't enforce the session limit. The agent must end the call at `MAX_SESSION_MINUTES`, which is 6 for the beta.

## ADR-6: Text-only storage with 90-day deletion

**Status:** Accepted

**Context:** Lee wants to review conversations, and visitors are told what's kept and for how long.

**Decision:** Store `invites`, `sessions`, `sessions/{id}/transcript` and `contacts`. Keep text only, with no audio or video. Contacts stay apart from transcripts. Everything about a visitor gets a `delete_at`, and Firestore TTL removes it. Invites get one too, because their labels can name a person. It is set at creation to expiry plus the retention period, so an invite outlives every session that points to it. Revoking an invite doesn't change it. Deletion requests are honoured sooner.

**Consequences:** The 90-day promise isn't enforced until the TTL config is deployed. Summaries are stored on the session, so they go with it. An invite and its label stay visible to the admin for up to 90 days after expiry.

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

**Status:** Accepted, partly built: `cloud-run`'s endpoints, webhook and summary are built; the agent doesn't send batches yet

**Context:** A crash shouldn't lose a conversation, and transcripts are untrusted input that can try to steer the tl;dr.

**Decision:** The agent sends turns in batches during the call. `cloud-run` writes the summary at the end, and a LiveKit `room_finished` webhook is the fallback if the agent dies. The summary step has no tools, and each summary links to its transcript.

**Consequences:** `cloud-run` gains two authenticated endpoints, each of which needs signature tests.

## ADR-10: Admin uses Google sign-in, verified by `cloud-run`

**Status:** Accepted

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

## ADR-13: shadcn/ui and Tailwind v4, one theme

**Status:** Accepted

**Context:** The design is a custom look that a styled component library would fight.

**Decision:** Use shadcn/ui on Radix, with Tailwind v4 tokens in `firebase/src/index.css`, and fonts installed as packages.

**Consequences:** There is one theme, with no light/dark switch. For now it is a plain white and grey placeholder; Lee has not chosen the final look. LiveKit's components still need mapping to these tokens.

## ADR-14: Public repo secret handling

**Status:** Accepted

**Context:** The repo is public, and tags and history are too.

**Decision:** Only `.env.example` files are committed. `.gitignore` and a pre-commit hook block secret files. Production secrets live in Secret Manager and LiveKit Cloud secrets. Lee's legal name and contact email are set through config, not code. Logs never contain transcripts, contact details, codes or tokens.

**Consequences:** The hook must be enabled in each clone. A leaked secret must be rotated, because deleting it from history isn't enough.

## ADR-15: Show the terms only after a valid code

**Status:** Accepted

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

**Decision:** The first release's terms are in English only, because each language needs its own reviewed consent text. The avatar itself speaks English and Spanish (ADR-20). It has no visitor recap page, because a recap needs its own access control and a mention in the terms. It has no shared-links panel, because that isn't needed to prove the flow.

**Consequences:** Spanish and Portuguese terms, the recap and shared links each get their own decision later. ADR-20 sets the limits for that language decision.

## ADR-18: Tag releases on `main`, one version for the repo

**Status:** Accepted

**Context:** Tags are only useful once they mark what's running.

**Decision:** Tag `v0.1.0` on `main` when the full flow works end to end: invite, consent, call and saved transcript. Use annotated tags and one version across all three targets. Move to `v1.0.0` when invites go to real employers.

**Consequences:** `dev` must merge to `main` before each release.

## ADR-19: The agent answers only from verified facts

**Status:** Accepted, partly built: facts and rules are in the prompt, and summaries list declined questions; grounding tests aren't built

**Context:** Given only a résumé, the model confidently answered cybersecurity questions Lee couldn't answer. A résumé says what Lee has done, not what Lee hasn't, so the model fills the gaps from its own knowledge. Anything it says in Lee's voice sounds like Lee's expertise, and that oversells Lee to recruiters.

**Decision:** The agent's knowledge is a set of facts that Lee reviews entry by entry. Each entry gives a topic, a level, what's verified and its limits. The set also lists skills Lee doesn't have, so a "no" is stated rather than guessed. ADR-21 sets where the facts live and how Lee edits them.

- Questions about Lee are answered only from the file.
- General technical questions aren't answered from the model's own knowledge, even when it knows the answer.
- Application-level security answers come from notes Lee wrote, so the model doesn't decide what counts as "application level".
- If something isn't covered, the agent says so plainly and points the visitor to Lee, without guessing or implying Lee knows it.
- The whole published set sits in the prompt, with no retrieval, because a missed lookup is when the model would improvise.
- Grounding tests run before each agent deploy, and a failure blocks it. They also run nightly against the published facts (ADR-21). They include unit tests with LLM judges, and simulated recruiters who push on missing skills.
- Each call summary lists the questions the agent declined, so Lee can decide what to verify and add.

**Alternative rejected:** A second model checking each answer during the call adds delay to a voice conversation. Tests and transcript review come first, and this can be revisited if they miss too much.

**Consequences:** Hallucinations are reduced, not eliminated, so transcript review stays part of the design. The avatar will decline questions a recruiter might expect it to handle. Declined questions must be identifiable in the transcript for the summary step to list them.

## ADR-20: Show language levels with real proof, not AI speech

**Status:** Accepted, partly built: the bilingual twin is built but not yet tried in a call; prepared Portuguese answers aren't built

**Context:** Lee's Spanish is fluent and Lee's Portuguese is about B2. Portuguese generated by the avatar would sound far better than B2 in a clone of Lee's voice, which misleads visitors. Making the AI add mistakes on purpose would be fake too. Lee still wants visitors to be able to hear real Portuguese.

**Decision:** The avatar never generates Portuguese. The fact file states each level, and the call screen shows a short, unscripted clip labelled "Lee's real voice, unedited". The clip is a static asset and collects nothing from visitors. The rollout has two stages:

1. **First release:** the avatar speaks English and Spanish, because Spanish matches Lee's real level. It switches to Lee's Spanish ElevenLabs voice when the visitor asks for Spanish or speaks it, and back when they ask for English. If asked to speak Portuguese, it stays in the call's language, gives Lee's level and points to the clip. Any other language gets an English reply.
2. **Next:** the avatar can answer a Portuguese question with one of 8–12 prepared answers, each recorded by Lee. The model only picks the answer, and code plays the recording word for word. The first one is preceded by a note that this is Lee's real voice, recorded in advance, and that Lee's conversational Portuguese is about B2. Any question without a matching answer gets a reply in the call's language, English or Spanish.

**Bilingual from the start (decided 2026-11-17):** Lee decided the avatar speaks Spanish without waiting for the Spanish terms, which replaces the earlier plan to add Spanish only after the translated consent text was reviewed. Until it is, every visitor agrees to the English terms, which describe the call in full whatever language it's held in. ADR-17's reviewed text per language applies to the terms, not to the language of the call.

**Terms language (added 2026-11-17):** The terms open in the first language in the browser's preference list that cloud-run offers, and in English otherwise. A switch above them changes the language, and shows only when more than one is offered. This differs from the redirect ADR-22 rejects: nothing redirects, there's no per-language URL to share, English is one tap away, and the choice isn't stored. cloud-run's `TERMS_LANGUAGES` setting decides what's offered, so a translation goes live only once it's reviewed. Each language has its own version, and the session records which language the visitor agreed in. cloud-run sends the visitor's terms language to the agent in the dispatch metadata, and the call opens in it. Speech recognition detects English or Spanish itself, and a `set_language` tool switches the voice.

**Alternative rejected:** Speaking Lee's written answers through the AI voice would use Lee's words, but the delivery would still sound better than B2.

**Consequences:** Lee has to record the clip, the answers and the note. Stage 2 depends on Portuguese speech recognition and on the Tavus avatar lip-syncing to recorded audio, and neither has been tested. Prepared answers sound smoother than spontaneous speech, so the note and the unscripted clip both stay. Recordings of Lee's voice are personal data that Lee chooses to publish, so they go through the knowledge review.

## ADR-21: Facts are edited in admin and fetched at call start

**Status:** Accepted, partly built: transcripts don't record the fact version yet, and the nightly run isn't built

**Context:** Lee will update the facts from time to time, often after seeing a question the avatar declined. Editing a file in the repo and redeploying the agent for each change is slow, and the repo is public, so the facts' whole history would sit in git.

**Decision:** The facts live in Firestore and are edited on the admin page. Under ADR-2, `cloud-run` does all reads and writes.

- Each entry is a draft or published. Only published entries ever reach the agent.
- Publishing creates a numbered version of the whole set. Lee can roll back to any earlier version in one step.
- When a call starts, the agent fetches the current published version from a signed `cloud-run` endpoint, the same way it sends transcripts. The whole set goes into the prompt for the call, as ADR-19 requires. Nothing is fetched per question.
- The agent keeps the last version it fetched. If the fetch fails, it uses that version. If it has none, it apologises and ends the call, because it can't answer without facts.
- Each transcript records the fact version the agent used, so Lee knows what it knew at the time.
- Each declined question in a summary (ADR-19, A5) has an "Add as fact" action that opens a draft with the question filled in. The draft copies only the question, never who asked it.
- Publishing takes effect on the next call, with no deploy. The grounding tests fetch the published facts, run before each agent deploy, and run nightly. A nightly failure notifies Lee, who fixes the entry or rolls back.
- The résumé-based draft in `livekit/facts/lee.yaml` is imported once to seed Firestore, then deleted from the repo.

**Alternative rejected:** Running the grounding tests on every publish, and going live only if they pass. It's safer, but each edit would wait minutes and cost a test run, and it needs `cloud-run` to trigger CI. Lee is the only author and reviewer, so a nightly check and one-step rollback are enough for now.

**Consequences:** A bad edit can be live until the nightly run catches it or Lee notices. The agent can't start a call while `cloud-run` is down and it has no cached version, but `cloud-run` issues the tokens anyway, so no call could start then. Facts are Lee's own content, not visitor data, so they have no `delete_at`. Anything published is still treated as public (ADR-7).

## ADR-22: The portfolio page is in English, Spanish and Portuguese

**Status:** Accepted

**Context:** Lee's work and YouTube channels reach Spanish and Portuguese speakers. ADR-17 keeps the first release's terms in English because each language needs its own reviewed consent text. The public portfolio page has no consent text and collects nothing.

**Decision:** The portfolio page is served at `/` (English), `/es` and `/pt`, with a language switcher in the header. Each language has its own URL so it can be shared, and nothing about the visitor's choice is stored. The invite flow and terms are in English until the Spanish terms are reviewed (ADR-17, ADR-20), and the call is in English or Spanish. The Spanish and Portuguese pages say that, and they claim nothing the English page doesn't. All three languages sit side by side in `firebase/src/landing/content.ts`, so an edit to one is visible in the others. Spanish and Portuguese use gender-neutral wording, and job and certificate titles stay as issued.

**Alternative rejected:** Choosing the language from the browser settings and redirecting. It hides the English page from people who want it and makes links depend on who opens them.

**Consequences:** Every change to the portfolio text needs all three languages. The translations need Lee's review, and the Portuguese needs a fluent reviewer too, because Lee's Portuguese is about B2 (ADR-20).

## ADR-23: The owner's profile is data, not code

**Status:** Accepted, partly built: `cloud-run` takes the owner's name from config and the facts seed from the profile

**Context:** The project will become open source, so anyone can run their own avatar. Today Lee's name, photos, portfolio text and greetings are written into the code, so anyone who forks it gets Lee's face and has to dig through the code to replace it.

**Decision:** Everything about the owner lives in one profile folder, and the code reads it.

- `profile.example/` is committed. It describes a sample owner who is clearly fake, with a placeholder silhouette photo, made-up jobs and sample facts, so a fork works out of the box and nobody ships Lee's face by accident.
- `profile/` is gitignored. Lee's real profile lives in a separate private repo and is checked out into `profile/` locally and in each deploy. When `profile/` is missing, each target falls back to `profile.example/`.
- The profile holds the owner's display name, links, domain, portfolio text in every language, images, audio clips, greetings and style prompt, and a facts seed file for the one-time import.
- `firebase` reads it at build time through a `@profile` import alias. `livekit` reads it from `PROFILE_DIR`, and the profile is bundled into the agent build. `cloud-run` gets the owner's name from config, as it already does for the legal name.
- Code, UI text and prompts never name the owner. They use the name from the profile.
- Facts stay in Firestore once imported (ADR-21). The legal name, contact email, and the Tavus and ElevenLabs IDs stay in config and secrets (ADR-14), because they're per-deploy settings, not content.

**Alternative rejected:** A private fork for Lee's site. It would drift away from the public repo with every change, and fixes would have to be copied across by hand. Putting all of it in env vars was also rejected, because images and three-language text don't fit in env vars.

**Consequences:** Each deploy needs one more checkout step. Tests run against `profile.example/`, so the sample has to stay complete, and any new kind of owner content must be added to the sample too. Lee's photos are still in git history. They're already public on the live site, so rewriting history is only about giving the open-source repo a clean start, and it's decided once, before that release. Existing docs say "Lee" and are renamed to "the owner" before release.

## ADR-24: Speech-to-text is AssemblyAI through LiveKit Inference

**Status:** Accepted

**Context:** The agent needs to turn the visitor's speech into text for the model and the transcript. ElevenLabs already makes the avatar's voice and also offers speech-to-text, and the first terms named it for both.

**Decision:** Speech-to-text uses AssemblyAI's `universal-3-6-pro` model through LiveKit Inference, set in `livekit/agent.py`. Pricing was a factor. Inference also needs no separate AssemblyAI account or API key, because usage is billed and rate-limited through LiveKit Cloud. ElevenLabs only makes the avatar's voice.

**Alternative rejected:** ElevenLabs speech-to-text, which would have kept speech and voice with one provider.

**Consequences:** AssemblyAI receives the visitor's speech, so the terms name it as a processor. Its data use and retention go on the same check as Gemini, ElevenLabs and Tavus. Changing the speech model or provider changes the terms, and that needs fresh consent (ADR-4). Speech recognition detects the spoken language, which the bilingual twin needs (ADR-20). Portuguese recognition still needs testing. The ai-coustics noise filter runs inside the agent and meters through LiveKit Cloud, so it isn't listed as a processor.
