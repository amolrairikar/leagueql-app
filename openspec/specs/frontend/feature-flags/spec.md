# feature-flags Specification

## Purpose
Provide a vendor-neutral frontend feature-flag layer using OpenFeature (`@openfeature/web-sdk`). Flags are resolved at runtime from the backend's public `GET /feature-flags` endpoint — so a console toggle reaches the SPA without a rebuild. There is no bundled config: the app fetches flags at bootstrap and fails safe to `false` until they resolve or whenever the backend is unreachable. Call sites depend only on the neutral `isEnabled` helper.

## Requirements

### Requirement: Fail safe to off
With flags unresolved or the backend unreachable, every flag SHALL read `false`, and an unknown flag SHALL evaluate to `false`.

#### Scenario: Flags unresolved or backend down
- **WHEN** flags have not resolved or the backend is unreachable
- **THEN** every flag reads `false` (feature off), and a transient outage never flips a flag on

#### Scenario: Unknown flag
- **WHEN** `isEnabled` is called for an unknown flag or a spec without `enabled`
- **THEN** it returns the `false` default

### Requirement: Resolve flags at runtime without a rebuild
Editing the feature-flag parameter SHALL change the UI within the refresh window without a rebuild, via a bootstrap fetch plus a light poll/visibility refresh.

#### Scenario: Runtime toggle
- **WHEN** the feature-flag parameter value is edited in the SSM console
- **THEN** the SPA picks up the change within the refresh window (poll + `visibilitychange`) without a reload/rebuild, soft-remounting the tree so synchronous `isEnabled()` call sites re-evaluate

### Requirement: Idempotent refresh
A refresh that resolves the same flag values SHALL NOT swap the provider or remount the app.

#### Scenario: No-change refresh
- **WHEN** a refresh (e.g. returning to the tab) resolves the same key-sorted flag values as currently applied
- **THEN** the provider is not swapped, no event is emitted, and the app does not remount (component state preserved)

### Requirement: No-op under Vitest
`initFeatureFlags()` SHALL be a no-op under Vitest so component tests never hit the network.

#### Scenario: Test environment
- **WHEN** the app runs under Vitest
- **THEN** `initFeatureFlags()` makes no `/feature-flags` fetch
