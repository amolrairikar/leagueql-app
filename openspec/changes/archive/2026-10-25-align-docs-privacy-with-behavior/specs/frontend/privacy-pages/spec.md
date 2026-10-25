# Spec Delta

## MODIFIED Requirements

### Requirement: Disclose Yahoo OAuth token storage

The general privacy page (`/privacy`) SHALL disclose Yahoo as a supported data source and SHALL state
that LeagueQL persists Yahoo OAuth access/refresh tokens encrypted at rest so it can refresh league
data, that these tokens are never sold or shared, that one Yahoo connection is shared by all of the
user's Yahoo leagues, and that the tokens are removed when the user deletes their last Yahoo league
(or can be revoked at any time from the user's Yahoo account settings).

#### Scenario: Yahoo token disclosure

- **WHEN** the general privacy page renders
- **THEN** it lists Yahoo among the fantasy platforms LeagueQL analyzes and states that Yahoo OAuth
  tokens are stored encrypted at rest (to refresh league data), never sold or shared, shared across
  the user's Yahoo leagues, and removed when the user's last Yahoo league is deleted or revocable
  from Yahoo account settings (without exposing internal encryption implementation details)

### Requirement: Disclose ESPN cookie storage when auto-refresh is enabled

The general privacy page (`/privacy`) SHALL state that ESPN cookies are stored (encrypted at rest)
only when the user enables automatic refresh for an ESPN league, are used solely to refresh that
user's league data, are never sold or shared, and are removed once none of the user's ESPN leagues
has automatic refresh on (because it was turned off or the league was deleted) — and that ESPN
cookies are not stored otherwise.

#### Scenario: ESPN storage disclosure

- **WHEN** the general privacy page renders
- **THEN** it states that ESPN cookies are stored encrypted at rest only when the user enables
  automatic refresh, used only to refresh league data, never sold or shared, removed once no ESPN
  league of the user's still has auto-refresh on, and not stored otherwise (without exposing
  internal encryption implementation details)

### Requirement: Accurately disclose ESPN cookie handling

The extension privacy page SHALL accurately state that ESPN cookies are read only for onboarding and
refresh, transmitted once over HTTPS, and never stored or logged by the extension itself, and SHALL
state that once the cookies reach LeagueQL they are stored on LeagueQL's servers only when the user
enables automatic refresh (encrypted at rest) and are otherwise not retained — staying consistent
with actual behavior. It SHALL name the autofill control by its actual label, "Autofill cookies
from ESPN".

#### Scenario: Cookie disclosure

- **WHEN** the extension privacy page renders
- **THEN** it describes ESPN cookie handling accurately: the extension reads them only for
  onboarding/refresh, transmits them once over HTTPS, and never stores or logs them; and on
  LeagueQL's servers they are retained only when the user enables automatic refresh (stored encrypted
  at rest) and are otherwise not stored — consistent with the app and extension's real data handling

#### Scenario: Autofill label matches the UI

- **WHEN** the extension privacy page describes triggering autofill
- **THEN** it refers to the "Autofill cookies from ESPN" button, the label the connect, refresh, and
  migrate forms actually render

## ADDED Requirements

### Requirement: Disclose diagnostics telemetry and every third-party processor

The general privacy page SHALL disclose that LeagueQL collects performance and error diagnostics
(pages visited within the app, request timings, page-load performance metrics, and errors, tagged
with the signed-in account ID) and SHALL list every third-party service that processes user data,
including Better Stack as the diagnostics provider.

#### Scenario: Diagnostics disclosure

- **WHEN** the general privacy page renders
- **THEN** it describes the diagnostics LeagueQL collects (including that they are tagged with the
  signed-in account ID) and its Third-Party Services list includes Better Stack alongside Clerk,
  ESPN, Sleeper, Yahoo, AWS, and Cloudflare

### Requirement: Disclose account-linked league data

The general privacy page SHALL disclose the account-linked data LeagueQL stores beyond league data:
which leagues a signed-in user owns or is a member of (including invite links), ownership-transfer
tokens, and the team a user claims as theirs on My Team, and SHALL state that sign-in may use
email/password or Google through Clerk.

#### Scenario: Account-linked data disclosure

- **WHEN** the general privacy page renders
- **THEN** it lists league ownership/membership and invite links, ownership-transfer tokens, and the
  My Team claim as stored data, and states that Clerk sign-in supports email/password and Google

### Requirement: Describe how deletion actually works

The general privacy page SHALL describe deletion as it works in the product: a league's owner can
permanently delete its data with the sidebar's Delete League action, and anyone else (including a
non-owner leaguemate, or someone wanting their account and membership data removed) can request
removal by emailing support.

#### Scenario: Deletion rights

- **WHEN** the general privacy page's rights section renders
- **THEN** it states that league owners can delete a league's data themselves via Delete League and
  that other removal requests (membership, account data, or a league whose owner is unreachable)
  go to the support email address
