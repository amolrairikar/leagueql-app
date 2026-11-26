## ADDED Requirements

### Requirement: Document unused-league removal
`/docs` SHALL include an "Unused League Removal" level-2 subsection under "Managing Your League" stating the one-year rule, what counts as opening a league, what is removed (including stored credentials under the same rules as manual deletion), that no advance notice is sent, and how to connect the league again.

#### Scenario: Removal section renders
- **WHEN** the docs page renders
- **THEN** the "Unused League Removal" subsection appears with its own table-of-contents entry, states that any member opening the dashboard resets the one-year period while automatic refreshes and appearing in My Leagues do not, lists what is removed, says no advance notice is sent, and explains connecting the league again
