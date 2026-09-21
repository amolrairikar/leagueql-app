## REMOVED Requirements

### Requirement: Surface onboarding and re-link states
**Reason**: The "coming soon" onboarding state is superseded — a linked Yahoo league now onboards
for real through the same pipeline as ESPN/Sleeper. This requirement is replaced by "Onboard a
linked Yahoo league", which drops the coming-soon notice, adds real onboarding + polling, and
keeps the reconnect behavior.
**Migration**: No user action. The connect flow now starts onboarding and polls the job to
completion instead of showing a "coming soon" notice; the `YAHOO_AUTH` reconnect prompt is
preserved.

## ADDED Requirements

### Requirement: Onboard a linked Yahoo league
Onboarding a linked Yahoo league SHALL start onboarding via `POST /leagues` with `platform=YAHOO`
and poll the returned job to completion (the same success/progress/error flow used for ESPN and
Sleeper), and SHALL surface a "Reconnect your Yahoo account" prompt on a `YAHOO_AUTH` re-link
signal.

#### Scenario: Onboard and poll to completion
- **WHEN** a linked Yahoo league is submitted and the backend returns `201` with a `correlation_id`
- **THEN** the UI polls job status and shows progress, then the completed league on success and an
  inline error alert on a `FAILED` job — with no "coming soon" notice

#### Scenario: Expired/revoked link
- **WHEN** onboarding returns the `YAHOO_AUTH` re-link signal (at submit time or as a `FAILED` job)
- **THEN** the UI shows a "Reconnect your Yahoo account" prompt that restarts the OAuth step rather
  than a generic failure
