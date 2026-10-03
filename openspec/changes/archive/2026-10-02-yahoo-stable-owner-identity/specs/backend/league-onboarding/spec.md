# Spec Delta

## MODIFIED Requirements

### Requirement: Parse Yahoo team, manager, and logo identities
The onboarder SHALL parse each team's identity, primary manager (owner id + display name), and
logo from the Yahoo `/teams` payload. Because Yahoo returns a collection either as a numeric-keyed
object (`{"0": {...}, "count": N}`, used for large collections like teams and roster players) or as
a plain list (`[{...}]`, used for small nested sub-collections like `managers` and `team_logos`),
the parsing SHALL handle both shapes so owner ids, display names, and logos populate. Each team's
primary-owner id SHALL be unique within the league: a team's manager `guid` SHALL be used when it
is real (not a masked value such as `--hidden--` or `--`, and not empty) and unique within the
league; otherwise that team's per-league `manager_id` SHALL be used. Each raw team row SHALL also
carry the real `guid` (null when masked or absent) and the Yahoo slot `manager_id` as separate
fields.

#### Scenario: Managers and logos parsed from list-shaped sub-collections
- **WHEN** a Yahoo `/teams` response returns each team's `managers` and `team_logos` as plain lists
- **THEN** each team's primary owner id, display name, and logo URL are populated (not null),
  and the derived member rows carry those owner ids

#### Scenario: Managers parsed from a numeric-keyed sub-collection
- **WHEN** a Yahoo sub-collection is instead returned as a numeric-keyed object
- **THEN** the same fields are parsed identically

#### Scenario: Masked or duplicate guids fall back to manager_id
- **WHEN** Yahoo returns a masked manager `guid` (e.g. `--hidden--`) or omits it for a team, or two
  teams in the same league report the same non-masked guid
- **THEN** each affected team's primary-owner id comes from its distinct per-league `manager_id`,
  so every team keeps a distinct owner and the correct manager name rather than collapsing onto
  the first, and a masked or absent guid is recorded as a null `guid` on the raw team row

#### Scenario: Distinct guids preserved for cross-season continuity
- **WHEN** a team's manager has a real guid that no other team in the league shares
- **THEN** that guid is used as the team's owner id, even if other teams in the league fall back
  to their `manager_id`, so that manager stays continuous across seasons

#### Scenario: Raw team row keeps guid and slot id separately
- **WHEN** a Yahoo season's teams are written to the raw season data
- **THEN** each team row carries `guid` (the real guid or null) and `slot_manager_id` (Yahoo's
  per-league `manager_id`) in addition to the resolved owner id
