# Spec Delta

## ADDED Requirements

### Requirement: Resolve stable Yahoo owner identities across seasons
The processor SHALL assign each person in a Yahoo league one owner id used in every season they
appear in, linking teams across seasons by real guid, then manager nickname, then team name, then
custom (non-default) team logo. A link SHALL be made only when exactly one earlier identity
matches and that identity is not already linked to another team in the same season. The owner id
SHALL be the person's real guid when known, otherwise the team key from their first season.

#### Scenario: Manager moves to a different slot
- **WHEN** a manager with nickname "Manager A" owns slot 10 in one season and slot 9 in the next
- **THEN** both seasons' teams carry the same owner id, and the manager who takes over slot 10
  gets a different owner id

#### Scenario: Title credited to the real winner
- **WHEN** "Manager B" wins a season in slot 12, leaves, and "Manager C" later takes slot 12 and
  wins another season
- **THEN** the standings mark each title under a different owner id, so each manager is credited
  with exactly one title

#### Scenario: Returning manager after a gap
- **WHEN** a manager plays one season, sits out one or more seasons, and then returns in another slot
- **THEN** the returning team is linked to the manager's earlier owner id

#### Scenario: Real guid takes precedence
- **WHEN** a team has a real guid that matches an earlier identity
- **THEN** it is linked by guid, even if its nickname or team name changed

#### Scenario: Masked or ambiguous nicknames never merge
- **WHEN** a manager's nickname is `--hidden--`, or two teams in the same season share a nickname
- **THEN** no link is made by nickname for those teams, and they are linked only by guid, team
  name, or custom logo, or else become new identities

#### Scenario: Team name or custom logo links a renamed manager
- **WHEN** a manager's nickname changes between seasons but their team name or custom logo URL is
  unchanged
- **THEN** the team is linked to the manager's earlier owner id

#### Scenario: Default logos are not used to link
- **WHEN** two teams in different seasons share a Yahoo default logo URL and nothing else
- **THEN** they are not linked

#### Scenario: New manager
- **WHEN** a team matches no earlier identity by any signal
- **THEN** it gets a new owner id equal to its own team key, or its real guid when it has one

#### Scenario: Legacy raw data without separate guid fields
- **WHEN** a raw Yahoo season file predates the separate `guid`/`slot_manager_id` fields
- **THEN** a non-numeric `manager_id` is treated as a real guid, and a numeric one is treated as
  a slot number to be linked by nickname, team name, and logo

### Requirement: Keep Yahoo owner ids consistent across incremental refreshes
When processing only some seasons of a Yahoo league, the processor SHALL resolve owner identities
using the team data of every season in the league, so owner ids written for seasons not being
reprocessed remain valid.

#### Scenario: Latest-season refresh keeps earlier ids
- **WHEN** a Yahoo league that was fully processed is refreshed and only its latest season is
  reprocessed
- **THEN** every manager's owner id in the reprocessed season equals the owner id already stored
  for that manager in earlier seasons

#### Scenario: New season appended
- **WHEN** a new Yahoo season is added and processed on its own
- **THEN** returning managers keep their existing owner ids and only new managers get new ids

### Requirement: Translate Yahoo migration mappings to stable owner ids
When a league migrated to Yahoo has a `PLATFORM_MIGRATION` mapping that has not yet been
translated, the processor SHALL rewrite each destination owner id from the id the Yahoo members
proxy returned to that manager's stable owner id, and SHALL mark the mapping as translated so it
is rewritten only once.

#### Scenario: Mapping translated on first processing
- **WHEN** a league migrated from another platform to Yahoo is processed for the first time
- **THEN** each mapping entry's destination owner id becomes the stable owner id of the Yahoo team
  that id identified in the latest season, entries marked `__not_returning__` are unchanged, and
  the mapping is flagged as translated

#### Scenario: Already-translated mapping left alone
- **WHEN** a Yahoo league whose mapping is already flagged as translated is processed again
- **THEN** the mapping is not modified
