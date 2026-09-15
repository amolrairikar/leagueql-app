## MODIFIED Requirements

### Requirement: Short-circuit when already up to date
The API SHALL return `409` when the league is already current, and SHALL degrade safely when NFL state cannot be fetched. "Already current" SHALL be judged against the latest **played** stored week — the most recent stored matchup week that has a real result (a non-zero score or a decided winner) — not the largest stored matchup key. Stored weeks that carry no played result (e.g. an ESPN league's pre-stored future-week schedule with 0–0 scores and no winner) SHALL NOT count toward "already current".

#### Scenario: NFL offseason
- **WHEN** NFL state `season_type == "off"`
- **THEN** the API returns `409` "League is already up to date (NFL offseason)."

#### Scenario: Already current
- **WHEN** the latest **played** stored matchup `(season, week)` is `>=` current NFL state
- **THEN** the API returns `409` "League is already up to date."

#### Scenario: Behind current with only unplayed later weeks stored
- **WHEN** the latest **played** stored matchup `(season, week)` is `<` current NFL state, even though later weeks are already stored with no played result (an ESPN league's pre-stored future-week schedule)
- **THEN** the up-to-date guard does not block, and the refresh is allowed to proceed

#### Scenario: NFL state fetch fails
- **WHEN** the NFL state fetch fails
- **THEN** the refresh is still allowed to proceed
