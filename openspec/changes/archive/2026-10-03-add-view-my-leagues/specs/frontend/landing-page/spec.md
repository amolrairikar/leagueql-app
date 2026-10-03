# Spec Delta

## ADDED Requirements

### Requirement: View My Leagues button
For a signed-in user, the hero SHALL show a "View My Leagues" button beside "Connect Your League" and "View Demo". It SHALL toggle an expandable panel below the buttons and expose its state with `aria-expanded`. Signed-out visitors SHALL NOT see it. Opening the panel SHALL close the Connect form, and opening the Connect form SHALL close the panel.

#### Scenario: Signed out
- **WHEN** a signed-out visitor loads `/`
- **THEN** no "View My Leagues" button is shown

#### Scenario: Expand and collapse
- **WHEN** a signed-in user activates "View My Leagues", then activates it again
- **THEN** the panel expands below the buttons with `aria-expanded="true"`, then collapses with `aria-expanded="false"`

#### Scenario: Mutually exclusive with Connect
- **WHEN** the panel is open and the user activates "Connect Your League"
- **THEN** the Connect form opens and the panel collapses, and the reverse also holds

### Requirement: List the user's leagues
When expanded, the panel SHALL fetch the user's leagues and list them in the returned order (most recently updated first). Each row SHALL show the platform logo, league name, platform, season span with season count, and when it was last updated. A migrated league SHALL note its source platform, and an owner's ESPN league needing re-auth SHALL show a "Reconnect ESPN" flag. Rows SHALL NOT show owner/member badges or filters.

#### Scenario: Leagues listed
- **WHEN** the panel opens and the API returns leagues
- **THEN** each league renders as a row with its logo, name, "Platform • first–last · N seasons • Updated …", in API order

#### Scenario: Migrated league row
- **WHEN** a returned league has `migrated_from` set
- **THEN** its row notes "Moved from <platform>"

#### Scenario: Re-auth flag
- **WHEN** a returned league has `espn_reauth_required` true
- **THEN** its row shows a "Reconnect ESPN" flag

#### Scenario: Missing-league hint
- **WHEN** the list renders
- **THEN** a hint below it reads "Missing a league? For ESPN or Yahoo, ask the league owner for an invite link. For Sleeper, open your league once using "Connect Your League" and it shows up here afterwards."

### Requirement: League list states
The panel SHALL show a loading skeleton while fetching. With no leagues, it SHALL show an empty state that explains how leagues get added and offers "Connect Your League". When the request fails, it SHALL show the error inline with a retry action, not in a global banner.

#### Scenario: Loading
- **WHEN** the leagues request is in flight
- **THEN** skeleton rows are shown

#### Scenario: Empty
- **WHEN** the API returns an empty list
- **THEN** an empty state with a "Connect Your League" action is shown, and that action opens the Connect form

#### Scenario: Request fails
- **WHEN** the leagues request fails with a `4xx` or `5xx`
- **THEN** an inline error with "Try again" is shown, and retrying re-requests the list

### Requirement: Open a league from the list
Activating a row SHALL open that league the same way the Connect flow opens an already-onboarded league: it loads the league's metadata for the row's `league_id` and `platform`, stores the league selection, and navigates to `/home`. A failure SHALL be shown inline without leaving the page.

#### Scenario: Open succeeds
- **WHEN** the user activates a league row
- **THEN** the league's selection is stored and the app navigates to `/home`

#### Scenario: Open fails
- **WHEN** loading the selected league's metadata fails (for example `403` after access was revoked)
- **THEN** an inline error is shown and the user stays on `/`
