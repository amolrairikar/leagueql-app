# Proposal

## Why

Yahoo leagues are refreshed by the scheduled auto-refresh only when the owner ticks an "enable
automatic weekly refresh" checkbox at connect time, and Yahoo has no manual Refresh League action
and no way to change that choice after onboarding. A Yahoo league connected with the box unchecked
is therefore frozen at its onboarding snapshot forever. The opt-in guards nothing: unlike ESPN
(where opting in means storing cookies we otherwise would not keep), the Yahoo OAuth token is
stored regardless because connecting requires it, and the Privacy Policy already discloses that it
is used to refresh league data.

## What Changes

- The scheduled auto-refresh SHALL select every in-season Yahoo league that has a resolvable owner,
  the same way Sleeper leagues are always selected — `auto_refresh_enabled` no longer gates Yahoo.
  Existing Yahoo leagues onboarded with the box unchecked start refreshing with no backfill.
- **BREAKING (UI)**: Remove the "enable automatic weekly refresh" checkbox (and its tooltip) from
  the Yahoo connect flow on the landing page, and drop carrying that opt-in across the OAuth
  consent redirect/popup. Nothing replaces it (no auto-refresh note on the connect form).
- Update the `/docs` Yahoo refresh section to say Yahoo leagues refresh automatically (no opt-in,
  no manual refresh).
- ESPN is unchanged: its auto-refresh stays opt-in with the checkbox, Refresh League dialog, and
  Turn Off Auto-Refresh action.
- Privacy Policy is unchanged (it already states Yahoo tokens are used to fetch and refresh league
  data).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/scheduled-league-auto-refresh`: Yahoo leagues are always selected in season (owner
  still required); the opt-in flag gates ESPN only.
- `frontend/connect-yahoo-league`: the auto-refresh opt-in checkbox requirement is replaced by one
  stating Yahoo has no opt-in (no checkbox, no note, no opt-in sent).
- `frontend/landing-page`: the Yahoo OAuth return no longer carries/applies an auto-refresh opt-in.
- `frontend/instructions-docs`: the Yahoo refresh sub-subsection documents always-on automatic
  refresh instead of an opt-in.

## Impact

- **Backend**: `src/league_refresh/utils.py` (`get_leagues_to_refresh` Yahoo branch); unit tests in
  `tests/unit/league_refresh/test_utils.py`; component scenarios in
  `tests/component/features/league_auto_refresh.feature` + steps.
- **Frontend**: `frontend/src/features/landing_page/landing-page.tsx` (Yahoo checkbox, opt-in
  plumbing), `frontend/src/features/connect_league/yahoo-auto-refresh-pref.ts` (removed),
  `frontend/src/features/instructions/instructions-page.tsx`; landing-page component tests
  (`landing-connect.feature` + steps, `static-pages.feature` if the docs copy is asserted).
- **Docs**: `docs/db/dynamodb_spec.md` / `docs/api/openapi_spec.yaml` descriptions of
  `auto_refresh_enabled` (now only meaningful for ESPN).
- **Operational**: more Yahoo leagues refreshed per weekly run → more Yahoo API calls and onboarder
  invocations; existing per-platform dispatch pacing applies.
- No API contract, DynamoDB schema, or infrastructure change.
