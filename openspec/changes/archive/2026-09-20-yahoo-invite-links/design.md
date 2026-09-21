## Context

See proposal.md — Why. The invite-link feature (mint on the owner side, redeem on `/join`) was
built ESPN-only. The read boundary it feeds — `require_league_member` in `src/api/helpers.py` —
already gates every platform except Sleeper, Yahoo included, and the data layer it writes
(`members` set + `invite_token_hash` on METADATA, `add_league_member`) is platform-agnostic. The
only things holding it to ESPN are explicit `platform != Platform.ESPN` guards in the two API
routes and a set of `=== 'ESPN'` / `!== 'ESPN'` checks plus ESPN-worded copy in the frontend.

## Goals / Non-Goals

**Goals:**
- Let Yahoo league owners mint invite links and Yahoo leaguemates redeem them, identically to ESPN.
- Express the gate as "not Sleeper" so the read-authorization model stays consistent with
  `require_league_member` and any future gated platform is covered without another code change.

**Non-Goals:**
- No new endpoint, data-model field, or migration.
- No change to how Yahoo data is onboarded — the owner's linked OAuth token still authorizes the
  fetch; an invitee needs no Yahoo link of their own (mirrors ESPN, where invitees need no cookies).
- Sleeper stays open-read and keeps returning `400` from the invite endpoints.

## Decisions

**Gate on `platform == SLEEPER` (reject), not on an ESPN/Yahoo allowlist.** The single source of
truth for "is this league gated" is already `require_league_member`, which no-ops only for
Sleeper. Mirroring that (invite endpoints reject only Sleeper) keeps the two authorization
surfaces from drifting and means a future gated platform is automatically invite-capable.
Alternative — an explicit `in (ESPN, YAHOO)` allowlist — was rejected because it would need
editing again for every new platform and could silently diverge from the read gate.

**Generalize requirements and UI copy instead of duplicating per platform.** The mechanism is
identical across platforms, so the specs rename the ESPN-specific requirements to platform-neutral
ones and the UI copy drops "ESPN cookies" in favor of "their own ESPN or Yahoo login." One code
path, one set of tests parameterized by platform.

**Frontend gates mirror the backend.** The sidebar invite action and the `/join` validity check
switch from `=== 'ESPN'` / `!== 'ESPN'` to `!== 'SLEEPER'` / `=== 'SLEEPER'`, so the UI never
offers or accepts an invite for a platform the backend would `400`.

## Risks / Trade-offs

- [A future platform is added that should NOT support invites] → The "not Sleeper" gate would
  auto-enable invites for it. Mitigation: the same assumption already governs
  `require_league_member`; any new platform must be slotted into that read-gate decision
  deliberately, and that is the correct single place to make the gated/open call.
- [Copy generalization touches shared ESPN strings] → Mitigation: frontend component tests assert
  the platform-neutral wording for both ESPN and Yahoo; the existing Sleeper-rejected scenarios
  are retained to lock the boundary.
