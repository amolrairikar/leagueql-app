## Why

Yahoo support launched with a "Beta" badge, a tooltip, and a connect-form support note. Several Yahoo leagues have now onboarded successfully, so the beta labeling no longer applies.

## What Changes

- Remove the "Beta" badge and its tooltip from the Yahoo chip in the landing "Works with" strip.
- Remove the Yahoo beta support note shown under the connect form when Yahoo is selected.
- Drop "(Beta)" from the Yahoo changelog entry.

## Capabilities

### Modified Capabilities
- `frontend/landing-page`: the "Works with" strip no longer marks Yahoo as Beta.

## Impact

Frontend only: `frontend/src/features/landing_page/`, `features/changelog/constants.ts`, and the matching component tests.
