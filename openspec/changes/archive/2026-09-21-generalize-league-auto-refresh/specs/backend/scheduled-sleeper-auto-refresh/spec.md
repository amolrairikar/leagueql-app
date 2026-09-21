# Spec Delta

## REMOVED Requirements

### Requirement: Auto-refresh Sleeper leagues in season
**Reason**: Renamed capability — generalized to Sleeper and Yahoo in `backend/scheduled-league-auto-refresh` ("Auto-refresh Sleeper and Yahoo leagues in season").
**Migration**: See `backend/scheduled-league-auto-refresh`; Sleeper behavior is unchanged.

### Requirement: Poll pending renewal lookups
**Reason**: Renamed capability — moved verbatim (Sleeper-only) to `backend/scheduled-league-auto-refresh`.
**Migration**: See `backend/scheduled-league-auto-refresh` ("Poll pending renewal lookups").

### Requirement: Skip legitimate no-op windows
**Reason**: Renamed capability — generalized ("no onboarded Sleeper or Yahoo leagues") in `backend/scheduled-league-auto-refresh`.
**Migration**: See `backend/scheduled-league-auto-refresh` ("Skip legitimate no-op windows").

### Requirement: Raise on indeterminate state or query failure
**Reason**: Renamed capability — moved to `backend/scheduled-league-auto-refresh` (alarm name generalized).
**Migration**: See `backend/scheduled-league-auto-refresh` ("Raise on indeterminate state or query failure").

### Requirement: Isolate per-league failures
**Reason**: Renamed capability — moved verbatim to `backend/scheduled-league-auto-refresh`.
**Migration**: See `backend/scheduled-league-auto-refresh` ("Isolate per-league failures").
