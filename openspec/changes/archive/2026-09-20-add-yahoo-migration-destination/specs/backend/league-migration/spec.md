## ADDED Requirements

### Requirement: Yahoo destination requirements
When the destination platform is Yahoo, the API SHALL require the caller to have a valid linked Yahoo token, SHALL NOT require `season`/`s2`/`swid`, and SHALL forward the owner's user id to the onboarder so the destination onboard can resolve the owner's Yahoo token.

#### Scenario: Yahoo destination without a link
- **WHEN** `POST /leagues/{leagueId}/migrate` targets a Yahoo destination and the caller has no valid linked Yahoo token
- **THEN** the API returns `403` "Link your Yahoo account first" and writes no migration records

#### Scenario: Yahoo destination needs no ESPN credentials
- **WHEN** the destination platform is Yahoo
- **THEN** the request does not require `season`, `s2`, or `swid`

#### Scenario: Owner id forwarded to the onboarder
- **WHEN** a Yahoo (or any) destination migration invokes the onboarder
- **THEN** the invocation carries the migrating owner's user id so the onboarder can resolve the Yahoo access token for the destination fetch
