## MODIFIED Requirements

### Requirement: Owner-gated sidebar actions
Owner-only actions SHALL be gated on `is_owner`, with non-owners seeing the alternate actions.
Invite Leaguemates SHALL additionally be gated on the league being an ESPN league, Refresh League
SHALL additionally be gated on the league being an ESPN league that is not enrolled in auto-refresh,
and Turn Off Auto-Refresh SHALL additionally be gated on the league being an ESPN league that is
enrolled in auto-refresh.

#### Scenario: Owner vs non-owner actions
- **WHEN** the sidebar renders for a league
- **THEN** Migrate, Transfer Ownership, and Delete are shown only when `is_owner` is true, Invite Leaguemates is shown only when `is_owner` is true and the league is an ESPN league, Refresh League is shown only when `is_owner` is true and the league is an ESPN league whose `auto_refresh_enabled` is false, Turn Off Auto-Refresh is shown only when `is_owner` is true and the league is an ESPN league whose `auto_refresh_enabled` is true, and non-owners see View Another League and Claim Ownership instead

## ADDED Requirements

### Requirement: Disable auto-refresh from the sidebar
The sidebar SHALL let the owner of an auto-refresh-enrolled ESPN league turn scheduled auto-refresh
off via a Turn Off Auto-Refresh action that opens a confirmation dialog and, on confirmation, calls
`PUT /leagues/{leagueId}/auto-refresh` with `enabled=false`. The dialog SHALL warn that the league
will stop refreshing automatically and that the stored ESPN login may be removed (requiring cookies
to be re-entered to opt back in). On success the league SHALL no longer be enrolled, restoring the
manual Refresh League action; on failure an inline error SHALL be surfaced and the dialog SHALL stay
open.

#### Scenario: Owner turns auto-refresh off
- **WHEN** the owner of an ESPN league whose `auto_refresh_enabled` is true confirms Turn Off Auto-Refresh
- **THEN** the app sends `PUT /leagues/{leagueId}/auto-refresh` with `enabled=false`, and on success the league is no longer enrolled and the manual Refresh League action is shown again

#### Scenario: Owner cancels
- **WHEN** the owner opens the Turn Off Auto-Refresh dialog and cancels
- **THEN** no request is sent and `auto_refresh_enabled` is unchanged

#### Scenario: Disable fails
- **WHEN** the `PUT /leagues/{leagueId}/auto-refresh` request fails
- **THEN** an inline error is shown, the dialog stays open, and the league remains enrolled
