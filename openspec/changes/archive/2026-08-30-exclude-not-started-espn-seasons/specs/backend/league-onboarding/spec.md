## ADDED Requirements

### Requirement: Exclude not-yet-drafted ESPN seasons
The onboarder SHALL exclude an ESPN season whose draft has not occurred (`draftDetail.drafted` is `false`) from the onboarded season list, and SHALL fail a brand-new ESPN onboard whose only season has not drafted with the same `NOT_STARTED` outcome used for not-yet-started Sleeper seasons. Because an ESPN league's completed prior seasons are the only ones reported as `previousSeasons`, the not-yet-drafted season can only be the latest season.

#### Scenario: Preseason latest season excluded from a multi-season league
- **WHEN** an ESPN league has one or more completed prior seasons plus a latest season whose `draftDetail.drafted` is `false`
- **THEN** the prior seasons onboard normally and the not-yet-drafted latest season produces no S3 payload, no processed views, and no season-dropdown entry

#### Scenario: New ESPN league whose only season has not drafted
- **WHEN** a brand-new ESPN onboard's only season has `draftDetail.drafted` of `false`
- **THEN** onboarding fails with the friendly `NOT_STARTED` message (templated for ESPN) rather than writing empty records, and no `draft_picks` view is registered for the processor
