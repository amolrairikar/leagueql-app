# Spec Delta

## MODIFIED Requirements

### Requirement: Handle the OAuth callback
`GET /leagues/yahoo/oauth/callback` (public — Yahoo redirects the browser here with no Clerk JWT) SHALL validate `state`, exchange the code for tokens as a PKCE public client (no client_secret), persist an encrypted token item, and redirect to the frontend page selected by the state's return-context `flow` — `/migrate_league` for `MIGRATE`, the landing page `/` otherwise (the `ONBOARD` default).

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates and consumes the single-use `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, `client_id`, the matching `redirect_uri`, and the stored PKCE `code_verifier` (no client_secret — Yahoo rejects a secret alongside PKCE), persists an encrypted `YAHOO_OAUTH` item keyed to the caller, and `302`-redirects to the flow's return page with `platform=YAHOO&yahooLinked=1` carrying the pending `leagueId`

#### Scenario: Onboard flow return
- **WHEN** the consumed `state` records `flow=ONBOARD` (or omits it)
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than `/connect_league`

#### Scenario: Migrate flow return
- **WHEN** the consumed `state` records `flow=MIGRATE`
- **THEN** the callback `302`-redirects to `/migrate_league?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than the landing page

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, already consumed, or mismatched
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=0` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `error=access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback consumes the echoed `state` to recover its return-context `flow`, `302`-redirects to that flow's page with `platform=YAHOO&yahooLinked=0` (falling back to the landing page `/` when no usable `state` is present), writing no partial token item and never reflecting an external redirect target
