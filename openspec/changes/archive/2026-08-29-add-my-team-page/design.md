# Design — My Team report card

## Context
All the underlying data is precomputed and already fetched by existing features. The design work is
(a) how the user selects "their" team given the app has no viewer→team mapping, (b) two
deterministic scoring modules that are new (overall grade, power rankings), and (c) the
rule-catalog engine that turns computed facts into written insights. No backend changes.

## Team selection (no "my team" exists)
`getLeague` returns only a league-level `is_owner` boolean — never the viewer's `owner_id`. So the
page cannot auto-detect the team; the user picks it.
- Reuse the roster/manager derivation from `manager-comparison.tsx` (built from `MATCHUPS` /
  `SEASON_STANDINGS`), keyed by `owner_id`, labelled by `owner_username` / display name.
- Persist the choice per league in `localStorage` under `myTeamOwnerId:{leagueId}` (new key added
  to `lib/cookie-handler.ts`, which currently stores only `leagueId`/`leaguePlatform`/
  `leagueSeasons`). Default to the first team (alphabetical by username) when unset or when the
  stored id is absent from the selected season.
- Join key across datasets is `team_id` (= `roster_id` for Sleeper transactions). A team's
  `team_id` can differ per season, so resolve the selected `owner_id` → that season's `team_id`
  from `SEASON_STANDINGS`.

## Overall grade — `compute-grade.ts`
Deterministic, league-relative, performance-weighted with a light management nod.
1. **Composite strength score** per team, each term normalized to 0–1 first:
   - all-play win % (`win_pct_vs_league`) — **0.40**
   - points-for **league percentile** (rank of `total_pf` among the league, 0–1) — **0.30**
   - actual win % (`win_pct`) — **0.20**
   - season **lineup efficiency** league percentile — **0.10** (lowest weight: nudges a borderline
     grade, never swings it alone)
2. Compute the composite for every team, then take the selected team's **percentile within the
   league** (ties share the higher percentile deterministically).
3. Map percentile → letter (bands, inclusive lower bound):
   `≥90 A · 82 A− · 73 B+ · 58 B · 50 B− · 40 C+ · 28 C · 14 C− · <14 D`.
   (An `A+` is reserved for the outright league leader at ≥97.) The grade tracks true strength, so a
   lucky team grades below its seed and an unlucky team above it — matching the page's thesis.

Rationale: weighting all-play + PF above actual record keeps the grade honest about how good the
team *is*, which the rest of the page argues the standings can hide.

## Power rankings — `compute-power-rankings.ts`
Computed entirely from a season's regular-season `MATCHUPS`. One score per team = normalized blend
of `avg_pf` (0.5), all-play win % (0.3, from each week's cross-league scoring), and **last-3-week
form** (0.2, from the team's last three results). Rank teams by score; movement = change in rank vs.
the same ranking recomputed through the previous week (matchups with `week < maxWeek`). Weights
documented here and unit-tested; this is the only net-new *metric* the page introduces.

## Insights — `compute-insights.ts` (rule catalog, not a snippet library)
Each insight *type* is one catalog entry:
```
{ id, sentiment: 'good'|'warn'|'bad',
  applies(metrics): boolean,          // does it fire for this team?
  score(metrics): number,             // severity/magnitude, for ranking
  render(metrics): { tag, headline, sentence, metric } }  // fills ONE parameterized template
```
Engine: run every rule → keep those where `applies` is true → sort by `score` desc → return top N.
The hero verdict is generated from the single top-ranked theme. Rules guard on data availability
(trade rules require `platform === 'SLEEPER'` and ≥1 trade) so no half-filled sentence renders.

Initial catalog (~12): luck (expected − actual wins), bench points left (lineup efficiency),
draft steal, draft bust, best trade, trade regret, tough/soft schedule (SoS), hot/cold streak,
elite scoring (PF rank), all-play overperformance, standing vs. power rank gap.

Everything is a pure function of the computed metrics → fully unit-testable ("given metrics, this
rule fires with this exact text"). Optional later: 2–3 deterministic phrasing variants per template
keyed by a hash of `team_id`.

## Extractions (no behavior change to existing pages)
- `draft_grades/draft-grades.tsx` best/worst-pick + steal/bust logic and its constants
  (`STEAL_DELTA_MIN`, `BUST_*`) → `draft_grades/compute-draft-grades.ts`; the page imports from it.
- `transactions/transactions.tsx` `sideTotal` / per-trade winner → `transactions/compute-trade-value.ts`;
  the page imports from it. Both refactors keep the existing pages pixel-identical and are covered
  by the existing (and slightly extended) tests.

## Lineup-efficiency aggregation
`computeStartSitReport` is per team-week. Aggregate across the selected team's weeks: sum optimal
and actual points → season efficiency = actualΣ / optimalΣ; total points left = optimalΣ − actualΣ.
Handle weeks lacking bench data (`hasBenchData === false`) by excluding them from the ratio.

## ESPN gating
`TRANSACTIONS` 404s on ESPN. The Trade Report renders a muted "Transactions are available on
Sleeper leagues" state, and trade-based insight rules do not fire. All other sections and the grade
(which does not depend on trades) work identically on both platforms.
