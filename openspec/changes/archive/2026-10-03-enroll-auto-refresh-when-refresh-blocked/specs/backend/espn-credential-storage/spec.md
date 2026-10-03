## MODIFIED Requirements

### Requirement: Store ESPN cookies encrypted at rest

The system SHALL persist a user's ESPN `SWID` and `espn_s2` cookies in a single per-user item
(`PK=USER#{clerk_user_id}, SK=ESPN_CREDENTIALS`) with both cookie values encrypted at rest, and
SHALL never write the plaintext cookies to logs, traces, API responses, or infrastructure config.
The credentials SHALL be stored only when the user opts a league into automatic refresh, and only
after the cookies have successfully authenticated against ESPN.

#### Scenario: Cookies stored on opt-in

- **WHEN** an ESPN onboard or refresh that opts into automatic refresh completes successfully
- **THEN** the owner's `SWID` and `espn_s2` are written to `USER#{clerk_user_id} / ESPN_CREDENTIALS`
  with both values encrypted at rest, replacing any previously stored values for that user

#### Scenario: Cookies stored on an opted-in blocked refresh

- **WHEN** an ESPN refresh that opts into automatic refresh is blocked (`409`/`429`) and the
  supplied cookies successfully authenticate against ESPN
- **THEN** the owner's `SWID` and `espn_s2` are written encrypted to
  `USER#{clerk_user_id} / ESPN_CREDENTIALS` even though no data refresh ran

#### Scenario: Plaintext never disclosed

- **WHEN** ESPN credentials are stored, read, or used
- **THEN** the plaintext cookie values appear in no logs, traces, API responses, or Terraform state

#### Scenario: Not stored without opt-in

- **WHEN** an ESPN onboard or refresh does not opt into automatic refresh
- **THEN** no `ESPN_CREDENTIALS` item is written from that request
