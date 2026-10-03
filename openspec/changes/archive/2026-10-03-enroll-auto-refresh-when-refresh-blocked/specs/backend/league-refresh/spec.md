## ADDED Requirements

### Requirement: Enroll auto-refresh when an opted-in refresh is blocked
When an ESPN refresh that opts into automatic refresh and supplies `swid` and `s2` is blocked by a
refresh in progress, the weekly cooldown, the NFL offseason, or the league already being up to
date, the API SHALL still validate the cookies against ESPN, store them encrypted, and set
`auto_refresh_enabled` on the league's `METADATA` before returning the original `409`/`429`. It
SHALL NOT invoke the onboarder for such a request. Cookies that ESPN rejects SHALL return `400`,
other ESPN failures SHALL return `502`, and a failure to store the cookies or set the flag SHALL
return `500`; in all of these cases the league SHALL NOT be enrolled.

#### Scenario: Opted-in refresh within the cooldown
- **WHEN** the league owner submits an ESPN refresh with `autoRefresh = true`, `swid` and `s2`
  fewer than 7 UTC calendar days after the last refresh, and ESPN accepts the cookies
- **THEN** the cookies are stored encrypted, `auto_refresh_enabled` is set to true, the onboarder
  is not invoked, and the API returns the usual `429` cooldown message

#### Scenario: Opted-in refresh blocked with a 409
- **WHEN** the same opted-in request is blocked because a refresh is in progress, the NFL is in its
  offseason, or the league is already up to date
- **THEN** the league is enrolled as above and the API returns the original `409` message

#### Scenario: Rejected cookies
- **WHEN** an opted-in blocked refresh supplies cookies that ESPN rejects with `401`/`403`
- **THEN** the API returns `400` asking the owner to re-enter their cookies, and no cookies are
  stored and `auto_refresh_enabled` is unchanged

#### Scenario: Blocked refresh without the opt-in
- **WHEN** a blocked refresh does not opt into automatic refresh or omits `swid`/`s2`
- **THEN** the API returns the original `409`/`429` without contacting ESPN or enrolling the league
