## Context

`compute-projection.ts` already enumerates every combination of the remaining **un-picked**
matchups to compute playoff odds (`computePlayoffOdds`, exact when `≤ MAX_EXACT_MATCHUPS`). Each
combination yields a full seeding via the same rule as `projectStandings` (wins desc → points-for
desc → team id). Clinching scenarios ask a related but different question — not "how likely" but
"what is *guaranteed* / *needed*" — so they reuse the same enumeration and seeding, add a per-team
classification, and render as plain-language lines.

## Key decisions

- **Only live, decisive teams are listed.** The section is about who is still fighting and what
  their next game means: **win & in** (a win makes them top-`num_playoff_teams` in every outcome),
  **must win** (a loss makes them miss in every outcome), or both (**controls its own destiny**).
  Teams with no clean self-determined line are omitted.
- **Rigorous tiebreaks — clinched means record alone.** Points-for keeps accumulating in the games
  still to play, so a same-record tie is never guaranteed by today's totals. A berth therefore
  counts as **clinched only when record alone secures it** (in every outcome, the number of teams
  with a record ≥ the team's is `≤ num_playoff_teams`). Symmetrically a team is **eliminated** only
  when record alone rules it out. Both are excluded from the list — the standings already convey
  them (the ✓ and the odds extremes).
- **Tie margins.** When a listed team's seat can come down to a same-record tie with specific
  rival(s), the scenario states the **current points-for gap** to each — the margin the rival would
  have to erase over the remaining games. This is the nuance beyond "win and in".
- **Conditional on picks.** Like odds, scenarios enumerate only the **un-picked** matchups (picks
  fold into the fixed base), and a team's conditioning game is its **earliest un-picked** matchup.
- **Exact only.** Guarantees ("in under *every* outcome") cannot be proven by sampling, so the
  section is computed only when the un-picked space is exactly enumerable (`≤ MAX_EXACT_MATCHUPS`),
  which comfortably covers a league's real race window; otherwise it is hidden.
- **Odds column unchanged (this change).** Today's odds break ties by *current* points-for, so a
  tie-favored team can read ~100% while its scenario is conditional. We tolerate that and add a
  one-line explainer (*odds = how likely; scenarios = what's mathematically locked*). A follow-up
  change will rebuild odds on a scoring-distribution simulation so the two agree exactly.
- **Clinched/eliminated exclusion is enumeration-based.** A team is excluded when it is top-N in
  every enumerated outcome (clinched) or in none (eliminated). The row ✓ keeps using the existing
  wins-alone `computeClinched` unchanged; the two definitions can disagree at a boundary tie (the
  wins-alone check ignores that a same-record tie could be lost on points), so reconciling the ✓
  with the rigorous view is deferred to the odds follow-up. In realistic (8+ team) leagues the
  bubble team is rarely wins-alone-clinched, so the difference seldom surfaces.

## Classification (per live team, over the enumeration)

For each combination, for team `T`: `strictlyBetter = #{wins_j > wins_T}`,
`tied = {j≠T : wins_j == wins_T}`, `seats = num_playoff_teams − strictlyBetter`. The combo is
`out` if `seats ≤ 0`, record-guaranteed `in` if `tied.length + 1 ≤ seats`, else a `tie`.
Splitting by `T`'s next-game bit: `win-and-in` iff every win-combo is `in`; `must-win` iff every
lose-combo is `out`; the tie rivals collected on the non-guaranteed branch (with `gap = pf[T] −
pf[rival]`) become the tie margins.

## Edge cases

- No live team qualifies, or the space is not exactly enumerable → the section is hidden.
- A team that both wins-in and loses-out is `controls-destiny` (no tie margin — clean both ways).
- Demo **replay** mode reuses the same model/logic; the demo dataset supplies real
  `LEAGUE_SETTINGS` and scored `MATCHUPS`, so margins compute without an "assumed" caveat.
