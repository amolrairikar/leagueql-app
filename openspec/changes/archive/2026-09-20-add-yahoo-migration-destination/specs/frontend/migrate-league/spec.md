## MODIFIED Requirements

### Requirement: Collect migration inputs and mapping
The flow SHALL confirm the source league, collect the destination platform + league ID, fetch destination members for mapping (ESPN via the ESPN members proxy, Yahoo via the Yahoo members proxy, Sleeper directly), and require every source manager to be mapped or marked not returning before submission.

#### Scenario: Build the migration
- **WHEN** the user proceeds through the flow
- **THEN** it confirms the source league, collects the destination platform + league ID, and builds a manager mapping

#### Scenario: ESPN destination members
- **WHEN** the destination is ESPN
- **THEN** its members are fetched via the ESPN members proxy and shown for mapping

#### Scenario: Yahoo destination members
- **WHEN** the destination is Yahoo and the caller has a valid Yahoo link
- **THEN** the destination league id is collected (no season/cookies), its managers are fetched via the Yahoo members proxy, and they are shown for mapping

#### Scenario: All managers mapped
- **WHEN** the user attempts to submit
- **THEN** submission is blocked until every source manager is mapped or explicitly marked not returning (`__not_returning__`)

## ADDED Requirements

### Requirement: Link Yahoo during migration
When the destination is Yahoo and the caller is not linked, the flow SHALL offer a Yahoo OAuth link and SHALL resume the wizard on return, auto-fetching members and advancing to the mapping step, without exposing any Yahoo token to the browser.

#### Scenario: Not linked prompts OAuth
- **WHEN** fetching Yahoo members returns the not-linked signal (`403`)
- **THEN** the wizard shows a "Connect with Yahoo" action that starts the Yahoo OAuth link with a migration return context

#### Scenario: OAuth return resumes the wizard
- **WHEN** the browser returns to `/migrate_league` with `platform=YAHOO&yahooLinked=1&leagueId=<id>`
- **THEN** the wizard restores the Yahoo destination with the league id prefilled, auto-fetches the members, and advances to the manager-mapping step

#### Scenario: OAuth declined
- **WHEN** the browser returns with `yahooLinked=0`
- **THEN** the wizard shows a cancelled/try-again message with the Yahoo destination and league id still available to retry the link
