## ADDED Requirements

### Requirement: No auto-refresh opt-in for Yahoo leagues

The Yahoo connect flow SHALL NOT offer an automatic-refresh opt-in (Yahoo leagues are always
refreshed in season; backend/scheduled-league-auto-refresh), and the Yahoo onboard request SHALL NOT
carry an automatic-refresh opt-in choice. The connect form SHALL NOT show any auto-refresh checkbox
or note when Yahoo is selected.

#### Scenario: No opt-in shown for Yahoo

- **WHEN** the user selects Yahoo in the connect form
- **THEN** no "enable automatic weekly refresh" checkbox and no auto-refresh note are shown

#### Scenario: No opt-in sent with the Yahoo onboard

- **WHEN** the user connects a Yahoo league (in place, or after the consent popup/redirect)
- **THEN** the `POST /leagues` request for that Yahoo league carries no automatic-refresh opt-in
  choice

## REMOVED Requirements

### Requirement: Opt a Yahoo league into automatic refresh

**Reason**: Yahoo leagues are now always auto-refreshed in season (backend/scheduled-league-auto-refresh).
The opt-in protected nothing — the Yahoo token is stored regardless — and an unchecked box left the
league with no refresh path at all, since Yahoo has no manual refresh action.

**Migration**: None required. Existing Yahoo leagues, whether or not they were opted in, are picked
up by the scheduled refresh automatically; the stored `auto_refresh_enabled` value is ignored for
Yahoo.
