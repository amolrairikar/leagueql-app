## Why

LeagueQL supports ESPN and Sleeper today. Yahoo Fantasy is the remaining major
platform managers ask for, but it requires an OAuth 2.0 handshake (unlike ESPN's
cookies or Sleeper's public API), so it is a larger, roadmap-level effort that is
**not yet officially committed**.

The `backend/yahoo-oauth` and `frontend/connect-yahoo-league` capability specs were
authored ahead of implementation during the initial OpenSpec migration and lived in
`openspec/specs/` as if they described shipped behavior. No Yahoo code has ever been
committed (no routes, no frontend, no OpenAPI paths, no Terraform; the platform enum
is `['espn', 'sleeper']`), so those live specs were drift — asserting `SHALL` behavior
the system does not have.

This change reclassifies that planned behavior as a **pending change proposal** (its
correct OpenSpec home) so that `openspec/specs/` again describes only implemented
capabilities. The Yahoo requirements are preserved here verbatim as the roadmap
target; the change stays open (unapplied, unarchived) until Yahoo support is built.

## What Changes

- **No code changes.** This is a spec-inventory correction plus a roadmap placeholder.
- Remove the two live capability specs `openspec/specs/backend/yahoo-oauth/` and
  `openspec/specs/frontend/connect-yahoo-league/`, which described unimplemented behavior.
- Carry their requirements into this change's delta specs under
  `## ADDED Requirements`, so archiving this change (once Yahoo ships) re-seeds both
  capabilities as implemented specs.

When Yahoo support is actually built, implement against these delta specs and follow
the normal apply → archive flow; archiving will merge them back into `openspec/specs/`.

## Capabilities

### New Capabilities
- `backend/yahoo-oauth`: OAuth 2.0 + PKCE authorize/callback, encrypted per-user token
  persistence, transparent refresh, and the "link Yahoo first" onboarding gate.
- `frontend/connect-yahoo-league`: Yahoo as a selectable Connect-League platform with a
  two-step link-then-onboard UX, re-link prompts, and demo-mode handling.

## Impact

- **Specs:** removes `openspec/specs/backend/yahoo-oauth/spec.md` and
  `openspec/specs/frontend/connect-yahoo-league/spec.md`; both are reproduced as delta
  specs in this change.
- **Code / infra / docs:** none in this change. Future implementation will touch
  `src/api/` (authorize/callback routes, `Platform` enum), a Yahoo client in the
  onboarder, `src/common/secrets.py`, KMS-encrypted `YAHOO_OAUTH` DynamoDB items,
  `frontend/src/features/connect_league/`, `docs/api/openapi_spec.yaml`,
  `docs/db/dynamodb_spec.md`, and the architecture diagram.
- **Roadmap status:** on the roadmap, not yet officially committed; this change remains
  open until then.
