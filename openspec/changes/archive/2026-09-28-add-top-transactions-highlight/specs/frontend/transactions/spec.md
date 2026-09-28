## ADDED Requirements

### Requirement: Highlight the season's top transactions
`/transactions` SHALL show a "Top transactions" section above the Summary table listing up to five
of the selected season's highest-impact moves across waivers, free agents, and trades together,
ordered by impact descending (earlier transaction first on a tie). A waiver or free-agent move's
impact SHALL be its net pickup value, and a two-team trade's impact SHALL be its winning margin,
credited to the winning team — both computed from the season's `MATCHUPS` box scores exactly as the
transaction cards compute them. Only moves with a positive impact SHALL be eligible; multi-team
trades and commissioner moves are never eligible. The section SHALL NOT change with the type
filter, and SHALL render nothing when no move is eligible or the matchup box scores are unavailable.

#### Scenario: Top moves across types
- **WHEN** a season has eligible waiver, free-agent, and trade moves and matchup box scores are
  available
- **THEN** the section shows at most five tiles ranked by impact descending, each with its rank,
  type, impact value, team, and the players added/dropped (for a trade, what the winning team
  received and gave up)

#### Scenario: Trade tile credits the winner
- **WHEN** an eligible two-team trade appears in the section
- **THEN** its tile shows the winning team, its winning margin labelled as won-by, and the losing
  team as the opponent

#### Scenario: Fewer than five eligible
- **WHEN** fewer than five moves have a positive impact
- **THEN** only those moves are shown; even trades and net-zero or net-negative pickups are omitted

#### Scenario: Nothing eligible
- **WHEN** no move in the season has a positive impact
- **THEN** the "Top transactions" section is not rendered

#### Scenario: Box scores unavailable
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the "Top transactions" section is not rendered and the rest of the page renders normally
  without an error

#### Scenario: Independent of the type filter
- **WHEN** the user changes the type filter
- **THEN** the "Top transactions" section is unchanged
