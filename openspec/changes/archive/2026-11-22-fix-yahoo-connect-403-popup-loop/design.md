# Design

## Context

`handleYahooConnect(leagueId)` in `use-landing-page.tsx` wraps the whole connect chain in one `try`: `onboardYahooLeague` (`POST /leagues`), job polling, then `getLeague` (`GET /leagues/{id}`). Its `catch` treats any `ApiError` with `status === 403` as "no Yahoo link" and calls `startYahooOauth`. But two different endpoints return `403` for different reasons: `POST /leagues` ("Link your Yahoo account first", `has_valid_link`) and `GET /leagues/{id}` ("Not a member of this league", `require_league_member`). Three callers re-enter `handleYahooConnect`: the form submit, the popup `postMessage` handler, and the page-return resume effect — so the misrouted `403` loops. See proposal.md for evidence and the specs for requirements.

The migrate-league wizard (`step2-new-platform-setup.tsx`) was checked: its only Yahoo `403` comes from `POST /leagues/{id}/yahoo_members`, which the backend returns solely for "link first" (a league missing from the account is `404`). It already routes correctly and needs no change.

## Goals / Non-Goals

**Goals:**
- A not-a-member `403` shows a clear, actionable inline message and never opens consent.
- Consent starts at most once per connect attempt, including across the popup and full-page-return paths.

**Non-Goals:**
- Changing backend behavior (for example making `POST /leagues` reject non-members for an already-onboarded league). A backend change would alter an API contract and is a separate decision.
- Automating invite redemption or showing an invite-link entry field here.
- Touching the ESPN/Sleeper connect paths or the migrate-league wizard.

## Decisions

- **Classify the `403` by call site, not by status alone.** Split `handleYahooConnect` so the `POST /leagues` call has its own `try/catch` (`403` → consent) and `getLeague` has its own (`403` → not-a-member message; anything else → generic error). Alternative: inspect the `403` `detail` text ("Link your Yahoo account first") — rejected as brittle string coupling to a backend message.
- **Reuse the ESPN member-gate wording.** "League already onboarded. Please reach out to your leaguemate who onboarded the league to get your league-specific invite link." is the existing, spec'd message for the same situation on ESPN, so the copy is consistent and already approved. It is shown through `setError`, which renders the shared `ErrorAlert` (no global banner, per the inline-error-handling convention).
- **Bound consent with an `afterConsent` argument, not component state.** `handleYahooConnect(leagueId, afterConsent = false)`. The popup `postMessage` handler and the return-resume effect pass `true`; when `true`, a "link first" `403` or `YAHOO_AUTH` failure sets an inline retry error and stops loading instead of calling `startYahooOauth`. A parameter is stateless, so it also holds across the full-page redirect/return path where a ref would be lost to the reload. Alternative: a counter ref — rejected because it resets on reload, leaving the redirect loop possible.
- **Error text after consent.** "Yahoo linking didn't complete. Please try again." reusing the existing retry phrasing style; a new submit calls `handleYahooConnect(id)` with the default `false`, so the user can retry.
- **Do not change `onboardYahooLeague`/`getLeague` API wrappers.** They already throw `ApiError` with `status`; no contract change.

## Risks / Trade-offs

- [A revoked token surfacing immediately after a fresh link is now an error, not a second consent] → That sequence indicates a real problem (Yahoo rejected a just-issued token); a bounded error beats an invisible loop, and the user can retry.
- [The not-a-member message mentions an invite link the user may not know how to get] → Mirrors the ESPN message and the My Leagues hint; owner-side invite minting already exists (`frontend/ownership-transfer`).
- [`getLeague` `403` could in theory also come from revoked access to a league the user previously belonged to] → The same message is accurate (they need a new invite).
- [Existing scenario "A revoked Yahoo link surfaced on return reopens the consent popup" encoded the loop] → Updated to assert the inline error; the first-attempt revoked-link scenario (not after consent) is unchanged.
