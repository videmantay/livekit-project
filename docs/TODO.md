# TODO

Project-wide work that belongs to no single deploy target.

Story numbers refer to [STORIES.md](STORIES.md), and ADR numbers to [ADRS.md](ADRS.md).

## Facts content

- [ ] Lee writes STAR stories for the main jobs and skills in admin, with results and numbers Lee confirms (ADR-19)
- [ ] Lee checks which programs can be named publicly, names those, and keeps the limits on the rest (ADR-7)

## Before the first invite

- [ ] Once the three workflows in `.github/workflows/` pass on GitHub, protect `main` so it requires them

- [ ] Create the LiveKit, Tavus, ElevenLabs and Firebase production setup
- [ ] Have a lawyer review the terms, including recording consent and AI disclosure rules
- [ ] Run one full call end to end, then tag `v0.1.0` on `main` (ADR-18)

## Open-source release

- [ ] Create the private profile repo for Lee and add the `profile/` checkout to each deploy (ADR-23)
- [ ] Rename "Lee" to "the owner" in the docs and code comments (ADR-23)
- [ ] Write a setup guide: copy `profile.example/`, fill it in, set the config (ADR-23)
- [ ] Decide whether to rewrite git history to remove Lee's photos before the release (ADR-23)
