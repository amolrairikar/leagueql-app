## Purpose

Stores a user's ESPN `SWID` and `espn_s2` cookies encrypted at rest so LeagueQL can refresh that
user's ESPN leagues on their behalf when they opt into automatic refresh, mirroring how Yahoo
OAuth tokens are protected.

## ADDED Requirements

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

#### Scenario: Plaintext never disclosed

- **WHEN** ESPN credentials are stored, read, or used
- **THEN** the plaintext cookie values appear in no logs, traces, API responses, or Terraform state

#### Scenario: Not stored without opt-in

- **WHEN** an ESPN onboard or refresh does not opt into automatic refresh
- **THEN** no `ESPN_CREDENTIALS` item is written from that request

### Requirement: Provide decrypted ESPN cookies to the owner's refresh

The system SHALL return a user's decrypted `SWID` and `espn_s2` when resolving them by
`clerk_user_id` for a scheduled ESPN refresh, and SHALL signal a re-authentication requirement
when no stored credentials exist for that user, so the scheduled refresh surfaces the existing
`ESPN_AUTH` failure rather than proceeding without cookies.

#### Scenario: Credentials resolved for the owner

- **WHEN** a scheduled ESPN refresh resolves the owner's stored credentials by `clerk_user_id`
- **THEN** the owner's decrypted `SWID` and `espn_s2` are returned for the fetch

#### Scenario: Missing credentials signal re-auth

- **WHEN** a scheduled ESPN refresh resolves credentials for a user who has no stored
  `ESPN_CREDENTIALS` item (never opted in, or their credentials were deleted)
- **THEN** a re-authentication requirement is signalled and the refresh records the `ESPN_AUTH`
  failure without dispatching a fetch

### Requirement: Delete ESPN cookies when no opted-in ESPN league remains

The system SHALL delete a user's `ESPN_CREDENTIALS` item once they have no remaining ESPN league
opted into automatic refresh, so encrypted credentials are not retained beyond their use. The
deletion SHALL be idempotent (a no-op when the item is absent).

#### Scenario: Last opted-in ESPN league removed

- **WHEN** a user turns off automatic refresh for, or deletes, their last ESPN league that was
  opted into automatic refresh
- **THEN** their `ESPN_CREDENTIALS` item (`PK=USER#{clerk_user_id}, SK=ESPN_CREDENTIALS`) is removed

#### Scenario: Other opted-in ESPN leagues remain

- **WHEN** a user turns off automatic refresh for one ESPN league but still has another ESPN league
  opted into automatic refresh
- **THEN** their `ESPN_CREDENTIALS` item is left intact
