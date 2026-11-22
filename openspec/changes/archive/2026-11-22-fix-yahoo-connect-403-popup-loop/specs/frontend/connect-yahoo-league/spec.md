# Spec Delta

## ADDED Requirements

### Requirement: Not-a-member outcome never starts Yahoo consent
When connecting a Yahoo league that is already onboarded, a `403` from reading the league (`GET /leagues/{id}`) — the caller is neither the owner nor a member — SHALL show an inline message telling the caller to ask the league owner for an invite link, SHALL stop the loading state, and SHALL NOT open the Yahoo consent popup or redirect to Yahoo. Only a `403` from the onboard call (`POST /leagues`, "Link your Yahoo account first") or a `YAHOO_AUTH` job failure SHALL start the consent step.

#### Scenario: Non-member connects an onboarded Yahoo league
- **WHEN** the caller is already linked, `POST /leagues` responds `200` "already onboarded", and `GET /leagues/{id}` responds `403`
- **THEN** an inline alert reads "League already onboarded. Please reach out to your leaguemate who onboarded the league to get your league-specific invite link.", loading stops, and no consent popup is opened and no authorize request is made

#### Scenario: Onboard-call 403 still starts consent
- **WHEN** `POST /leagues` responds `403` "Link your Yahoo account first"
- **THEN** the consent popup flow starts as before

#### Scenario: Other read failures show the generic error
- **WHEN** `GET /leagues/{id}` fails with a non-`403` error (network or `5xx`) after onboarding
- **THEN** the generic connect error is shown, loading stops, and no consent popup is opened

### Requirement: Consent retry is bounded
The Yahoo connect flow SHALL start the consent step at most once per connect attempt. After a consent round-trip has completed (the popup reported back, or the page returned from a full-page consent redirect), a further "link first" `403` or `YAHOO_AUTH` failure SHALL show an inline error asking the user to try again, SHALL stop the loading state, and SHALL NOT reopen consent.

#### Scenario: Link signal persists after consent
- **WHEN** the consent popup reports a successful link, and the resumed onboard still responds `403` "link first" or fails with `YAHOO_AUTH`
- **THEN** an inline error is shown, loading stops, and no second consent popup is opened

#### Scenario: Fresh attempt may start consent again
- **WHEN** the user submits the connect form again after such an error
- **THEN** a new connect attempt may start consent once, as for any first attempt
