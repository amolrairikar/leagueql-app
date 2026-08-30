/**
 * Overall team grade (frontend/my-team) — pure, no I/O.
 *
 * A deterministic, league-relative letter grade. Each team gets a composite
 * strength score = 0.40·all-play win % + 0.30·points-for percentile + 0.20·actual
 * win % + 0.10·lineup-efficiency percentile (efficiency the lowest weight, so it
 * nudges a borderline grade but never swings it alone). The team's percentile among
 * the league's composites maps to a letter. Because it leans on all-play and
 * points-for over raw record, a lucky team grades below its seed and an unlucky team
 * above it.
 */
import type { SeasonStandingsItem } from '@/components/api/types';

const W_ALLPLAY = 0.4;
const W_PF = 0.3;
const W_WIN = 0.2;
const W_EFF = 0.1;

export interface GradeResult {
  letter: string;
  /** Composite strength score, 0–1. */
  composite: number;
  /** League percentile of the composite, 0–100. */
  percentile: number;
}

/**
 * Percentile rank (0–1) of each value within the set, using
 * (strictly-worse + 0.5·equal) / n so ties share a deterministic percentile.
 */
function percentileRanks(values: Map<string, number>): Map<string, number> {
  const entries = [...values.entries()];
  const n = entries.length;
  const out = new Map<string, number>();
  for (const [id, c] of entries) {
    let worse = 0;
    let equal = 0;
    for (const [, v] of entries) {
      if (v < c) worse += 1;
      else if (v === c) equal += 1;
    }
    out.set(id, n > 0 ? (worse + 0.5 * equal) / n : 0);
  }
  return out;
}

/** Map a 0–100 percentile to a letter grade (see design.md bands). */
export function letterForPercentile(percentile: number): string {
  if (percentile >= 97) return 'A+';
  if (percentile >= 90) return 'A';
  if (percentile >= 82) return 'A−';
  if (percentile >= 73) return 'B+';
  if (percentile >= 58) return 'B';
  if (percentile >= 50) return 'B−';
  if (percentile >= 40) return 'C+';
  if (percentile >= 28) return 'C';
  if (percentile >= 14) return 'C−';
  return 'D';
}

/**
 * Grade every team in the league. `efficiencyByTeam` maps team_id → season lineup
 * efficiency (0–1); a team missing from it (no bench data) is treated as league-median
 * (0.5 percentile) for the efficiency term only.
 */
export function computeGrades(
  standings: SeasonStandingsItem[],
  efficiencyByTeam: Map<string, number>,
): Map<string, GradeResult> {
  const out = new Map<string, GradeResult>();
  if (standings.length === 0) return out;

  const pfById = new Map(standings.map((s) => [s.team_id, s.total_pf]));
  const pfPct = percentileRanks(pfById);
  const effPct = percentileRanks(efficiencyByTeam);

  const composites = new Map<string, number>();
  for (const s of standings) {
    const composite =
      W_ALLPLAY * s.win_pct_vs_league +
      W_PF * (pfPct.get(s.team_id) ?? 0) +
      W_WIN * s.win_pct +
      W_EFF * (effPct.get(s.team_id) ?? 0.5);
    composites.set(s.team_id, composite);
  }

  const compositePct = percentileRanks(composites);
  for (const s of standings) {
    const percentile = (compositePct.get(s.team_id) ?? 0) * 100;
    out.set(s.team_id, {
      letter: letterForPercentile(percentile),
      composite: composites.get(s.team_id) ?? 0,
      percentile,
    });
  }
  return out;
}

/** The grade for one team, or null when it is not in the standings. */
export function gradeForTeam(
  standings: SeasonStandingsItem[],
  efficiencyByTeam: Map<string, number>,
  teamId: string,
): GradeResult | null {
  return computeGrades(standings, efficiencyByTeam).get(teamId) ?? null;
}
