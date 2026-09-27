# Spec Delta

## MODIFIED Requirements

### Requirement: Start the authorization flow
`GET /leagues/yahoo/oauth/authorize` (Clerk-authenticated) SHALL return a Yahoo consent URL carrying the OAuth + PKCE parameters and bind a single-use `state` to the caller, carrying the pending league id, a return-context `flow`, and a `display` mode (`page` or `popup`) so the callback can resume on the correct frontend page and choose how to hand the result back.

#### Scenario: Authorize URL
- **WHEN** an authenticated caller hits `GET /leagues/yahoo/oauth/authorize` with a `leagueId`
- **THEN** it returns a `.../oauth2/request_auth` URL carrying `client_id`, the registered `redirect_uri`, `response_type=code`, a PKCE `code_challenge` with `code_challenge_method=S256` (Yahoo requires PKCE), and a single-use `state` bound to the caller (and to the pending `leagueId`), with the PKCE `code_verifier` persisted server-side with a short TTL

#### Scenario: Return-context flow carried
- **WHEN** the caller supplies `flow=MIGRATE` (or omits it)
- **THEN** the single-use `state` records the return context (`MIGRATE`, defaulting to `ONBOARD` when omitted) so the callback can choose the return page

#### Scenario: Display mode carried
- **WHEN** the caller supplies `display=popup` (or omits it)
- **THEN** the single-use `state` records the display mode (`popup`, defaulting to `page` when omitted) so the callback returns a `postMessage` page for `popup` and a `302` redirect for `page`

#### Scenario: Unauthenticated caller
- **WHEN** an unauthenticated caller hits the authorize endpoint
- **THEN** it returns `401`

### Requirement: Handle the OAuth callback
`GET /leagues/yahoo/oauth/callback` (public — Yahoo redirects the browser here with no Clerk JWT) SHALL validate `state`, exchange the code for tokens as a PKCE public client (no client_secret), persist an encrypted token item, and hand the result back to the frontend by the mode selected by the state's `display`: for `page` a `302` redirect to the frontend page selected by the return-context `flow` (`/migrate_league` for `MIGRATE`, the landing page `/` otherwise), and for `popup` an HTML page that `postMessage`s the linked/declined result to the opener and closes. A missing/invalid state (no recoverable `display`) SHALL fall back to the `page` redirect.

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates and consumes the single-use `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, `client_id`, the matching `redirect_uri`, and the stored PKCE `code_verifier` (no client_secret — Yahoo rejects a secret alongside PKCE), and persists an encrypted `YAHOO_OAUTH` item keyed to the caller

#### Scenario: Onboard flow page return
- **WHEN** the consumed `state` records `flow=ONBOARD` (or omits it) and `display=page`
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than `/connect_league`

#### Scenario: Migrate flow return
- **WHEN** the consumed `state` records `flow=MIGRATE`
- **THEN** the callback `302`-redirects to `/migrate_league?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than the landing page

#### Scenario: Popup return posts the result to the opener
- **WHEN** the consumed `state` records `display=popup`
- **THEN** the callback responds with an HTML page whose inline script `postMessage`s `{ source: "yahoo-oauth", platform: "YAHOO", yahooLinked, leagueId }` to the opener at the frontend's exact origin and then closes the window, and whose response carries a Content-Security-Policy that permits only that nonce-tagged inline script

#### Scenario: Popup opened without an opener self-redirects
- **WHEN** a `display=popup` callback page runs with no usable `window.opener` (the consent was opened in the same tab because the popup was blocked)
- **THEN** its script instead navigates the current tab to the `page`-mode return URL (`/?platform=YAHOO&yahooLinked=…&leagueId=…`) so onboarding still resumes inline

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, already consumed, or mismatched
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=0` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `error=access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback consumes the echoed `state` to recover its return-context `flow` and `display`, hands back a not-linked (`yahooLinked=0`) result in that mode (a `302` for `page`, a `postMessage` page for `popup`; falling back to the landing page `/` when no usable `state` is present), writing no partial token item and never reflecting an external redirect target
