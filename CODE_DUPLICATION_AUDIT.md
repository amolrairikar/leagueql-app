# Code Duplication Audit

_Generated 2026-09-23. Covers `src/` (Python), `frontend/src/` (React/TS),
`extension/src/`, and `workers/`. Tests, `dist/`, and `node_modules/` excluded._

## Method

Ran `jscpd` (min 8 lines / 60 tokens) for exact clones — **42 clones, ~771
duplicated lines (2.08%)** — then read each cluster to separate genuine,
refactorable duplication from unavoidable/false-positive overlap (shared import
blocks, boilerplate that reads better inline). Findings below are ordered by
priority = (impact of consolidating) × (breadth) ÷ (risk). File:line references
were current at audit time.

---

## P1 — High priority

### 1. Season-scoped data-fetch boilerplate (`useMemo` + `toResult`) — most pervasive

The same promise-building block is repeated across nearly every feature page:

```ts
const xPromise = useMemo(
  (): Promise<XResult> =>
    leagueId && selectedSeason
      ? toResult(getX(leagueId, platform, selectedSeason).then((r) => r.data), 'Failed to load ...')
      : Promise.resolve({ ok: true as const, data: [] }),
  [leagueId, platform, selectedSeason],
);
```

Seen in `season-standings.tsx:497-534` (twice, back to back),
`transactions.tsx:810-841`, `draft-grades.tsx:737-751`,
`draft-recap.tsx:597-611`, and the other season-driven features. jscpd flags the
season-standings↔transactions pair (#7) and draft-grades↔draft-recap pair (#5),
but the pattern is far broader than those two clones.

- **Why it matters:** this is the single most repeated shape in the frontend;
  error-message drift and inconsistent empty-state handling are easy to
  introduce.
- **Recommendation:** add a `useSeasonQuery(leagueId, platform, season, fetcher, errorMsg)`
  hook (or a `seasonQuery(...)` factory) in `frontend/src/lib/` that encapsulates
  the guard, `toResult`, and the empty `{ ok: true, data: [] }` fallback. Collapses
  ~10-15 call sites to one line each.

### 2. `draft-grades.tsx` and `draft-recap.tsx` share their whole bootstrap

Beyond clone #1 above, the two draft features share the component preamble
verbatim — `getLeagueCookies()`, `isDemoMode()`, `defaultSeason` sort,
`selectedSeason`/`demoAuction` state, and the identical `draftPromise`
(`draft-grades.tsx:727-755` ≡ `draft-recap.tsx:587-615`, and again at
`draft-grades.tsx:260-282` ≡ `draft-recap.tsx:356-378`). They differ only in the
container max-width and downstream rendering.

- **Recommendation:** extract a `useDraftData()` hook (cookies + demo toggle +
  season + `draftPromise`) consumed by both. Highest-density single refactor
  available.

### 3. `matchup-records.tsx` and `player-records.tsx` are near-twin components

The largest raw clones in the repo (#1: 65 lines, #2: 36 lines, plus ~10 smaller
ones) are between these two "record board" features. Shared verbatim:
`buildColorMap` (`matchup-records.tsx:73` ≡ `player-records.tsx:39`), the
`EMPTY_MATCHUPS` sentinel, the `extractRecords`/`extractEntries` loop skeleton,
and much of the JSX for the record-card grid, season selector, and empty/error
states.

- **Why it matters:** two ~550-line files evolving in lockstep; the 13 clone
  pairs between them mean most edits must be applied twice.
- **Recommendation:**
  - Move `buildColorMap` to `frontend/src/lib/matchups.ts` (which already houses
    `isUnplayedMatchup`) — see finding #5.
  - Factor the shared card-grid + season-selector + empty-state shell into a
    `<RecordBoard>` component parameterized by the record-type config array and a
    row extractor.

### 4. Yahoo JSON normalization helpers redefined in three places

`_flatten`, `_collection_items`, and `_league_subresource` exist in
`src/common/yahoo_members.py:31-89`, are **already imported** from there by
`src/onboarder/yahoo_client.py:30-33`, but are **re-implemented locally** in
`src/yahoo_player_stats_refresher/handler.py:41-70` (clones #29, #40) with the
comment _"kept local so this task deploys independently."_

- **Why it matters:** that Lambda already imports `from common.secrets` and
  `from common.yahoo_tokens` (its Dockerfile vendors `common/` to `/app/common`),
  so the local copies are unnecessary — and the copies have already drifted
  (`_collection_items` in the refresher dropped the list-shaped-container branch
  the canonical version has, a latent parsing bug if it ever hits that shape).
- **Recommendation:** delete the local defs and
  `from common.yahoo_members import _flatten, _collection_items, _league_subresource`.
  Consider relocating the three parsers to a dedicated `src/common/yahoo_parse.py`
  (they aren't members-specific) and re-exporting.

---

## P2 — Medium priority

### 5. Deterministic avatar-color assignment reimplemented several times

The "sort entities → assign `avatarColor(i)`" pattern recurs:
`buildColorMap` in `matchup-records.tsx:73` and `player-records.tsx:39`
(team-keyed), and the owner-keyed variant in `home-page.tsx:123-141` ≡
`manager-history.tsx:342-356` (clone #24, plus #41).

- **Recommendation:** add `assignAvatarColors(sortedIds: string[]): Map<string,string>`
  to `lib/color-constants.ts`, and a `buildTeamColorMap(matchups)` in
  `lib/matchups.ts`. Both call sites for teams and both for owners collapse to it.

### 6. `getSeasonMatchups` duplicated across three `api-calls.ts` files

Byte-identical (modulo a doc comment) in `matchups/api-calls.ts:31`,
`schedule_swap/api-calls.ts:7`, and `weekly_awards/api-calls.ts:7` (clone #28) —
each just wraps `queryLeague<MatchupItem>(leagueId, platform, \`MATCHUPS#${season}#\`)`.

- **Recommendation:** define it once (e.g. in `components/api/leagues.ts` or a
  shared `features/.../matchup-queries.ts`) and import it in all three features.

### 7. Static content pages share full scaffolding

`changelog-page.tsx`, `privacy-page.tsx`, and `extension-privacy-page.tsx` repeat
the same shell (clones #3, #4, #6): back button, `useEffect(scrollTo(0,0))`,
`scrollToSection`, sticky TOC `<aside>`, and container layout — differing only in
the section list and body.

- **Recommendation:** a `<TocPageLayout sections={...}>{children}</TocPageLayout>`
  component. Removes the shared `scrollToSection` and TOC markup from all three.

### 8. `_fetch` async skeleton duplicated between onboarder platform clients

`ESPNClient._fetch` (`onboarder/espn_client.py:340-359`) and
`SleeperClient._fetch` (`onboarder/sleeper_client.py:358-377`) share signature,
docstring, and the semaphore/session scaffolding (clone #35); they diverge only
in header handling and response shaping.

- **Recommendation:** a small `AsyncPlatformClient` base (or a
  `fetch_one(session, semaphore, url_data, *, headers, parse)` helper in
  `onboarder/utils.py`) holding the concurrency plumbing. Check whether
  `yahoo_client.py`'s fetch loop can share it too.

### 9. Owner-metadata GSI3 pagination scan duplicated in `api/helpers.py`

Two functions (`api/helpers.py:384-394` and `:427-437`, clone #37) run the same
paginated `table.query` over `GSI3` with `SK == METADATA` +
`owner_user_id` filter and the `while True / ExclusiveStartKey` loop, differing
only in the per-item predicate.

- **Recommendation:** a private generator
  `_iter_owner_metadata(clerk_user_id)` yielding items; each caller filters. Also
  guards against the two loops drifting in pagination handling.

### 10. Clipboard-copy-with-timeout logic duplicated in ownership dialogs

`handleCopy` (set `copied`, reset after 2000ms) is identical in
`ownership/invite-link-dialog.tsx:58-63` and
`ownership/transfer-ownership-dialog.tsx:43-48` (clone #27), and they're the only
two clipboard users in the app.

- **Recommendation:** a `useCopyToClipboard()` hook returning `{ copied, copy }`.

---

## P3 — Low priority (contained / SQL)

### 11. `processor/queries.py` — repeated SQL blocks

The heaviest single-file internal duplication (clones #8, #13, #15, #20, #31,
#36, #38 among others). Two recurring shapes:
- **ESPN vs SLEEPER query variants** identical except the trailing `WHERE`
  (e.g. `PLAYOFF_BRACKET` at `queries.py:172-220`).
- **Symmetric `team_a`/`team_b` UNION ALL** projections
  (`queries.py:418-440` ≡ `675-697`, `531-550`, etc.).

- **Assessment:** real, but SQL is a case where DRY-ing (Python string
  composition / shared CTE fragments) often hurts readability and reviewability
  more than the duplication costs. Lower priority; if addressed, prefer named,
  well-commented f-string fragments for the shared SELECT lists and the
  symmetric-teams CTE only — not full query templating.

### 12. `onboarder/writer.py` internal clone

`writer.py:228-240` ≡ `309-321` (clone #30) — repeated write/format block.
Small; fold into a local helper when next touched.

### 13. Intra-file JSX row clones in `matchup-records.tsx` and `playoff-bracket.tsx`

Adjacent near-identical blocks: `matchup-records.tsx:142-158/158-174`,
`174-186/190-202`, `280-291/294-305` (clones #17, #25, #32) and
`playoff-bracket.tsx:658-680/680-702`, `297-305/574-582` (#12, #42).

- **Assessment:** typically two-sided renders (team A / team B, bracket halves).
  Extract a small `<TeamRow>` / `<BracketSlot>` where it reduces edit surface;
  otherwise low value.

---

## Not actionable (false positives)

- **Clone #14** (`league-connect.tsx:12-32` ≡ `migrate-league.tsx:6-26`) is a
  shared shadcn/ui **import block** (`Select`, `Tooltip`, `Card`, …). Expected;
  not real logic duplication.
- Various small clones inside a single feature that are the natural symmetric
  A/B render already noted in #13.

---

## Suggested sequencing

1. **#4** (delete drifted Yahoo copies) — low risk, removes a latent bug.
2. **#1 + #2** (`useSeasonQuery` / `useDraftData` hooks) — biggest breadth.
3. **#5 + #6** (color + matchup query utils into existing `lib/`) — quick wins.
4. **#3 + #7** (component extraction: `<RecordBoard>`, `<TocPageLayout>`).
5. **#8, #9, #10** as those areas are next touched.
6. Treat **#11 (SQL)** as optional / readability-guarded.
