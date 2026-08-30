## Context

See proposal.md — Why. The ESPN onboarder resolves seasons in `ESPNClient._get_league_seasons` by fetching the latest season with `?view=mTeam` and reading `status.previousSeasons`; `self.seasons = previousSeasons + [latest_season]`. Draft state lives under a different ESPN view (`mDraftDetail` → `draftDetail`), which today is only fetched later, per-season, as the `draft_picks` data type (`_filter_draft_picks` reads `data["draftDetail"]["picks"]`).

Two invariants make this tractable:
- ESPN reports only **completed** seasons in `previousSeasons`, so every season except `latest_season` has necessarily drafted. Detection therefore only ever needs to inspect the latest season.
- The handler's not-started handling is already platform-generic: `handler.py:274` gates on `onboarding_service.client.get_seasons()` being empty, failing `ONBOARD` with `NOT_STARTED` and treating `REFRESH`/`MIGRATE` as a no-op `COMPLETED`. `is_new_season_refresh` (and the Sleeper pending-league logic it guards) is only ever set for Sleeper, so ESPN falls through that branch cleanly.

## Goals / Non-Goals

**Goals:**
- Exclude a not-yet-drafted ESPN latest season from `get_seasons()` so it is never fetched, written to S3, processed, or shown in the dropdown.
- Reuse the existing `NOT_STARTED` failure and no-op refresh paths — no new handler branch, no new job-status code, no new UI.

**Non-Goals:**
- Changing Sleeper behavior (its `pre_draft`/`drafting` requirement stays as-is).
- Making the processor tolerate an empty ESPN `draft_picks` view. With the exclusion in place the processor should never receive one; the `_filter_draft_picks` hardening is defense-in-depth, not the primary fix.
- Auto-attaching the ESPN season once its draft completes (a later normal refresh onboards it naturally, since ESPN links seasons via `previousSeasons`).

## Decisions

**1. Detect draft status during season resolution, not after fetching.**
Add `mDraftDetail` to the existing latest-season status request in `_get_league_seasons` (ESPN accepts multiple `view` params: `?view=mTeam&view=mDraftDetail`), read `draftDetail.drafted`, and drop `latest_season` from the returned list when it is `false`. This keeps excluded seasons out of `_build_all_request_urls` entirely, so no payload is fetched or written — matching "no S3 payload, no processed views, no dropdown entry."
- *Alternative rejected:* fetch everything, then post-filter after `fetch_all`. Wasteful (fetches settings/matchups/players for a season we discard) and forces reconciling `self.seasons` after construction.

**2. Apply the same check on the refresh branch.**
The constructor short-circuits refresh to `self.seasons = [latest_season]` without calling `_get_league_seasons`. Route the refresh path through the same latest-season draft-status check so a refresh of a pre-draft current season yields an empty `get_seasons()` and lands on the existing no-op `COMPLETED` success (the league keeps its existing data). This also prevents the `_filter_draft_picks` `KeyError` from ever firing during a refresh.

**3. Harden `_filter_draft_picks` defensively.**
Change `data["draftDetail"]["picks"]` to tolerate an absent `picks` key (e.g. `data.get("draftDetail", {}).get("picks", [])`). With decisions 1–2 the processor should never see an empty ESPN `draft_picks` view, but this removes the sharp `KeyError` edge if an undrafted season ever reaches this filter.

## Risks / Trade-offs

- **Extra view on the season-resolution request** → `mDraftDetail` is added to a request already being made; no new round-trip. Low cost.
- **Draft-in-progress (`drafted: false, inProgress: true`)** → still excluded (drafted is false), consistent with treating a league as onboardable only once its draft has produced picks. Acceptable; mirrors Sleeper's `drafting` exclusion.
- **A league drafts mid-onboard** → the season is simply picked up on the next refresh; no partial/empty draft is ever written. Acceptable.
