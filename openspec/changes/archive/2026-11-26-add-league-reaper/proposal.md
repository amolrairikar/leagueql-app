## Why

Leagues that nobody opens still use DynamoDB and S3 storage. Access has been tracked since
backend/league-access-tracking, so idle leagues can now be removed automatically.

## What Changes

- A new nightly, prod-only league reaper removes leagues idle for one calendar year (from
  `last_accessed_at`, or `onboarded_at` when never opened).
- It ships in dry-run mode and posts a Discord summary whenever leagues are eligible. There is
  no per-run cap.
- League deletion logic is shared between the API and the reaper. This also fixes the manual
  delete only removing the first 1,000 raw S3 objects.
- The landing-page FAQ, `/docs`, and `/privacy` describe the removal.

## Capabilities

### New Capabilities

- `backend/league-reaper`: scheduled removal of unused leagues.

### Modified Capabilities

- `backend/delete-league`: drop the obsolete league-count requirement.
- `frontend/landing-page`: FAQ entry about unused-league removal.
- `frontend/instructions-docs`: "Unused League Removal" docs subsection.
- `frontend/privacy-pages`: disclose the retention rule.

## Impact

New `src/league_reaper/` Lambda and IAM role, new `src/common/league_deletion.py`, API delete
path, Terraform, CI packaging, architecture diagram, and frontend copy.
