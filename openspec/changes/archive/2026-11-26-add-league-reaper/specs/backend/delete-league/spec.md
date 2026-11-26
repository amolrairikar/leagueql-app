## REMOVED Requirements

### Requirement: Decrement the global league count
**Reason**: No stored league counter exists; the landing-page count is derived from the GSI3 index (backend/app-stats-league-count), and the delete path never decrements one.
**Migration**: None.
