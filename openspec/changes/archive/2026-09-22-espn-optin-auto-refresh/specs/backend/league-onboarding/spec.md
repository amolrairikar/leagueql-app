## ADDED Requirements

### Requirement: Persist the auto-refresh opt-in on onboard and refresh

When an onboard or refresh request carries an automatic-refresh opt-in choice, the onboarder SHALL
persist it as `auto_refresh_enabled` on the canonical league's `METADATA` item so the scheduled
refresh can honor it. The choice SHALL be preserved across a new-season refresh (it SHALL NOT be
reset when a renewed season is registered).

#### Scenario: Opt-in recorded on onboard

- **WHEN** an ESPN or Yahoo onboard/refresh request indicates the owner is enabling automatic refresh
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is set to true

#### Scenario: Opt-out recorded on onboard

- **WHEN** an ESPN or Yahoo onboard/refresh request indicates automatic refresh is not enabled
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is set to false

### Requirement: Store the owner's ESPN cookies when opting into auto-refresh

When an ESPN onboard or refresh opts into automatic refresh and completes successfully, the
onboarder SHALL store the owner's `SWID` and `espn_s2` cookies encrypted at rest so a later
scheduled refresh can reuse them, storing them only after the cookies have successfully fetched the
league's data.

#### Scenario: Cookies persisted after a successful opted-in ESPN onboard

- **WHEN** an ESPN onboard/refresh that opts into automatic refresh fetches the league successfully
- **THEN** the owner's ESPN cookies are stored encrypted for reuse by the scheduled refresh

#### Scenario: Cookies not persisted on failure

- **WHEN** an ESPN onboard/refresh that opts into automatic refresh fails to authenticate against ESPN
- **THEN** no ESPN cookies are stored

### Requirement: Use the owner's stored ESPN cookies for a scheduled refresh

When an ESPN refresh is invoked with an `owner_user_id` and no cookies (the scheduled-refresh path),
the onboarder SHALL fetch and decrypt that owner's stored ESPN cookies to perform the fetch, and
SHALL record the existing `ESPN_AUTH` failure (which does not page on-call) when the owner has no
stored cookies or the stored cookies no longer authenticate.

#### Scenario: Scheduled ESPN refresh uses stored cookies

- **WHEN** an ESPN refresh is invoked with an `owner_user_id` and no cookies in the request
- **THEN** the onboarder fetches and decrypts that owner's stored ESPN cookies and uses them to
  refresh the league

#### Scenario: Missing or expired stored cookies

- **WHEN** a scheduled ESPN refresh finds no stored cookies for the owner, or the stored cookies are
  rejected by ESPN
- **THEN** the refresh records an `ESPN_AUTH` failure without paging on-call
