## ADDED Requirements

### Requirement: Refetch every season on a backfill refresh
When a `REFRESH` event carries `refetchAll=true`, the onboarder SHALL fetch every season of the
league's history from the platform rather than only the latest season. It SHALL overwrite each
season's raw S3 file under the existing canonical league ID, preserve the league's METADATA
(owner, members, and auto-refresh opt-in), and flag the manifest so the processor rebuilds
every season's views. The onboarder SHALL ignore `refetchAll` on `ONBOARD` and `MIGRATE`
requests.

#### Scenario: Refetch-all refresh fetches the full history
- **WHEN** the onboarder runs a `REFRESH` with `refetchAll=true` for an onboarded league
- **THEN** the platform client resolves every season (ESPN `previousSeasons` plus the latest
  season, the full Sleeper `previous_league_id` chain, or the full Yahoo `renew` chain), each
  fetched season's `{season}.json` is rewritten under the existing canonical prefix, the manifest
  carries `reprocess_all=true`, and METADATA owner and members are unchanged

#### Scenario: Default refresh still fetches only the latest season
- **WHEN** the onboarder runs a `REFRESH` without `refetchAll`
- **THEN** only the latest season is fetched from the platform

#### Scenario: Refetch flag ignored outside REFRESH
- **WHEN** an `ONBOARD` or `MIGRATE` event carries `refetchAll=true`
- **THEN** the onboarder handles it exactly as it would without the flag
