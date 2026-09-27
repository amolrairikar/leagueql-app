## MODIFIED Requirements

### Requirement: Onboard a league
A user SHALL be able to onboard a public Sleeper or ESPN league with platform + league ID. For ESPN, the season is derived automatically (see "Derive the ESPN season automatically") rather than entered by the user. ESPN onboarding of a not-yet-onboarded league begins inline on the landing page (frontend/landing-page), and refreshing an existing ESPN league happens through the in-dashboard Refresh League dialog (frontend/navigation-sidebar); both derive the season automatically. There is no standalone ESPN/Sleeper onboard/refresh form.

#### Scenario: Onboard a public league
- **WHEN** a user submits a valid platform and league ID
- **THEN** the league is onboarded via `POST /leagues`, with the ESPN `season` supplied automatically

#### Scenario: Pre-filled fields locked
- **WHEN** the Refresh League dialog opens for the currently-viewed league
- **THEN** it is scoped to that league — there are no editable platform/league-ID fields to change

### Requirement: Opt an ESPN league into automatic refresh

The ESPN landing-page onboard and the in-dashboard Refresh League dialog SHALL each present an "enable automatic weekly refresh" checkbox with an explanatory tooltip, defaulting to off. When checked, the opt-in SHALL be sent with the `POST /leagues` submit so the owner's cookies are stored for reuse; when unchecked, the opt-out SHALL be sent. The tooltip SHALL explain that enabling stores the ESPN cookies encrypted to refresh the league weekly during the season and that cookies can expire, occasionally requiring re-entry.

#### Scenario: Checkbox present with tooltip

- **WHEN** the ESPN landing-page onboard or the Refresh League dialog renders
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining that the
  ESPN cookies are stored encrypted, the league is refreshed weekly during the season, and cookies
  can expire and occasionally need re-entering

#### Scenario: Default off for a new onboard

- **WHEN** a user onboards a new ESPN league on the landing page
- **THEN** the automatic-refresh checkbox defaults to unchecked (opt-in)

#### Scenario: Prefilled from current enrollment on refresh

- **WHEN** the Refresh League dialog opens for an existing ESPN league the caller owns
- **THEN** the checkbox reflects that league's current `auto_refresh_enabled` state — which, because the dialog is only shown for a not-enrolled league, defaults to unchecked

#### Scenario: Choice sent with submit

- **WHEN** the user submits the ESPN landing-page onboard or the Refresh League dialog
- **THEN** the automatic-refresh opt-in choice is included in the `POST /leagues` request body
