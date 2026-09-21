# Design

## Context

See proposal.md — Why. The landing-page connect form (`handleConnectSubmit` in
`frontend/src/features/landing_page/landing-page.tsx`) branches on `platform`.
Its `YAHOO` branch currently calls `getYahooAuthorizeUrl` and full-page-redirects
to Yahoo's consent screen unconditionally; the OAuth-return leg
(`YahooConnectReturn`) then resumes onboarding. The Sleeper branch, by contrast,
calls `onboardLeague('ONBOARD', ...)` and `pollForCompletion` in place under the
existing `loading` progress UI.

Relevant existing backend contract (no change needed): `POST /leagues` with
`platform=YAHOO` 403s an unlinked caller ("Link your Yahoo account first") as its
first check, before any lookup or job creation (`src/api/routes.py`); returns
`200` with null `data` for an already-onboarded league; and a linked-but-revoked
token surfaces as a `YAHOO_AUTH` job failure during the async fetch.

## Goals / Non-Goals

**Goals:**
- A linked Yahoo caller onboards in place with the Sleeper-style progress bar and
  lands on `/home`, never re-visiting the consent screen.
- Preserve the OAuth redirect for genuinely unlinked callers.

**Non-Goals:**
- No change to the OAuth-return leg (`YahooConnectReturn`) — it still handles the
  redirect-back path for unlinked callers.
- No change to the migrate-league Yahoo flow.
- No new backend endpoint or API-contract change.

## Decisions

**Decision: Detect link status by optimistically calling `POST /leagues` first,
not by adding a link-status endpoint.**
The onboard endpoint already gates unlinked callers with a side-effect-free `403`,
so the frontend can treat that `403` as the "not linked → redirect to OAuth"
signal and any success as "linked → onboard in place." Rationale: reuses the
existing gate, adds no backend surface, and keeps token/link state entirely
server-side (no link status exposed to the browser, consistent with the
"no tokens in browser" requirement).
- *Alternative considered:* a `GET /leagues/yahoo/oauth/status` endpoint the form
  checks before deciding. Rejected: more backend surface and an extra round-trip
  for the same information the onboard `403` already conveys.

**Decision: Reuse the existing landing-page `loading` progress UI and
`pollForCompletion`.** The linked path mirrors the Sleeper branch exactly
(onboard → poll → `getLeague` → `setLeagueCookies` → navigate `/home`), so the
user sees the same progress messaging.

**Decision: Route `YAHOO_AUTH` job failures to the OAuth (re)link redirect.** A
stored link with a revoked refresh token passes the `403` gate but fails the async
job with `YAHOO_AUTH`; treat that like "not linked" and send the user through the
consent redirect rather than a generic failure.

## Risks / Trade-offs

- **Extra round-trip for unlinked callers** (an onboard `POST` that 403s before the
  redirect) → Acceptable: it is a single fast call with no side effects, and the
  brief `loading` state resolves straight into the redirect.
- **Divergence from `YahooConnectReturn`'s handling** (two places now interpret the
  onboard result) → Mitigated by mirroring the same result-handling shape
  (correlation_id → poll, null data → straight to `/home`, `YAHOO_AUTH` → relink).
