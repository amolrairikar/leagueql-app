## MODIFIED Requirements

### Requirement: Start the authorization flow
`GET /leagues/yahoo/oauth/authorize` (Clerk-authenticated) SHALL return a Yahoo consent URL carrying the OAuth + PKCE parameters and bind a single-use `state` to the caller, carrying the pending league id and a return-context `flow` so the flow can resume on the correct frontend page after the callback.

#### Scenario: Authorize URL
- **WHEN** an authenticated caller hits `GET /leagues/yahoo/oauth/authorize` with a `leagueId`
- **THEN** it returns a `.../oauth2/request_auth` URL carrying `client_id`, the registered `redirect_uri`, `response_type=code`, a PKCE `code_challenge` with `code_challenge_method=S256` (Yahoo requires PKCE), and a single-use `state` bound to the caller (and to the pending `leagueId`), with the PKCE `code_verifier` persisted server-side with a short TTL

#### Scenario: Return-context flow carried
- **WHEN** the caller supplies `flow=MIGRATE` (or omits it)
- **THEN** the single-use `state` records the return context (`MIGRATE`, defaulting to `ONBOARD` when omitted) so the callback can choose the return page

#### Scenario: Unauthenticated caller
- **WHEN** an unauthenticated caller hits the authorize endpoint
- **THEN** it returns `401`

### Requirement: Handle the OAuth callback
`GET /leagues/yahoo/oauth/callback` (public — Yahoo redirects the browser here with no Clerk JWT) SHALL validate `state`, exchange the code for tokens as a PKCE public client (no client_secret), persist an encrypted token item, and redirect to the frontend page selected by the state's return-context `flow` — `/migrate_league` for `MIGRATE`, `/connect_league` otherwise.

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates and consumes the single-use `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, `client_id`, the matching `redirect_uri`, and the stored PKCE `code_verifier` (no client_secret — Yahoo rejects a secret alongside PKCE), persists an encrypted `YAHOO_OAUTH` item keyed to the caller, and `302`-redirects to the flow's return page with `platform=YAHOO&yahooLinked=1` carrying the pending `leagueId`

#### Scenario: Migrate flow return
- **WHEN** the consumed `state` records `flow=MIGRATE`
- **THEN** the callback `302`-redirects to `/migrate_league?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than `/connect_league`

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, already consumed, or mismatched
- **THEN** the callback `302`-redirects to `/connect_league?platform=YAHOO&yahooLinked=0` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `error=access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback consumes the echoed `state` to recover its return-context `flow`, `302`-redirects to that flow's page with `platform=YAHOO&yahooLinked=0` (falling back to `/connect_league` when no usable `state` is present), writing no partial token item and never reflecting an external redirect target
