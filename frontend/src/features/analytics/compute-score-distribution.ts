import type { MatchupItem } from '@/components/api/types';

/** A manager's box-and-whisker stats over their regular-season weekly scores. */
export interface BoxStats {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  /** All regular-season scores for this manager, ascending. */
  scores: number[];
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  iqr: number;
  /** Most extreme scores still within the Tukey fences (the whisker ends). */
  whiskerLow: number;
  whiskerHigh: number;
  /** Scores outside `q1 - 1.5*iqr` … `q3 + 1.5*iqr`, ascending. */
  outliers: number[];
}

export interface ScoreDistributionData {
  /** Managers sorted by median desc, tie-broken on username. */
  teams: BoxStats[];
  /** Smallest score across all managers (for a shared x-scale), or 0 when empty. */
  globalMin: number;
  /** Largest score across all managers (for a shared x-scale), or 0 when empty. */
  globalMax: number;
}

/** A regular-season game is one with no playoff tier (`NONE` or absent). */
function isRegularSeason(m: MatchupItem): boolean {
  return !m.playoff_tier_type || m.playoff_tier_type === 'NONE';
}

interface TeamMeta {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
}

/**
 * Linear-interpolation quantile ("type 7", matching d3.quantile / numpy default)
 * over an array sorted ascending. `p` is in [0, 1].
 */
export function quantile(sorted: number[], p: number): number {
  if (sorted.length === 0) return NaN;
  if (sorted.length === 1) return sorted[0];
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

/**
 * Build per-manager weekly-score box-plot stats from a season's matchups (FE-033).
 *
 * Each matchup contributes its two scored sides as (team, score) points. Only
 * regular-season games count; byes (a side with no finite score) and self-matchup
 * placeholders (`team_a_id === team_b_id`) are skipped. Quartiles use linear
 * interpolation; whiskers extend to the most extreme points within the Tukey
 * fences (`q1 - 1.5*iqr` … `q3 + 1.5*iqr`), and points beyond the fences are
 * outliers. Managers are sorted by median desc, tie-broken on username.
 */
export function computeScoreDistribution(
  matchups: MatchupItem[],
): ScoreDistributionData {
  const meta = new Map<string, TeamMeta>();
  const scoresByTeam = new Map<string, number[]>();

  for (const m of matchups) {
    if (!isRegularSeason(m)) continue;
    // Skip self-matchup placeholders and byes (a side with no finite score), so
    // they never enter a distribution — mirrors `sides()` in compute-awards.ts.
    if (m.team_a_id === m.team_b_id) continue;
    if (
      !Number.isFinite(Number(m.team_a_score)) ||
      !Number.isFinite(Number(m.team_b_score))
    ) {
      continue;
    }

    for (const side of ['a', 'b'] as const) {
      const id = m[`team_${side}_id`];
      const score = Number(m[`team_${side}_score`]);
      if (!scoresByTeam.has(id)) scoresByTeam.set(id, []);
      scoresByTeam.get(id)!.push(score);
      // Names/logos can change across weeks; keep the latest seen.
      meta.set(id, {
        teamId: id,
        ownerUsername: m[`team_${side}_display_name`],
        teamName: m[`team_${side}_team_name`],
        teamLogo: m[`team_${side}_team_logo`],
      });
    }
  }

  const teams: BoxStats[] = [];
  for (const [id, raw] of scoresByTeam) {
    const scores = [...raw].sort((a, b) => a - b);
    const min = scores[0];
    const max = scores[scores.length - 1];
    const q1 = quantile(scores, 0.25);
    const median = quantile(scores, 0.5);
    const q3 = quantile(scores, 0.75);
    const iqr = q3 - q1;
    const lowFence = q1 - 1.5 * iqr;
    const highFence = q3 + 1.5 * iqr;

    const whiskerLow = scores.find((s) => s >= lowFence) ?? min;
    let whiskerHigh = max;
    for (const s of scores) {
      if (s <= highFence) whiskerHigh = s;
    }
    const outliers = scores.filter((s) => s < lowFence || s > highFence);

    teams.push({
      ...meta.get(id)!,
      scores,
      min,
      q1,
      median,
      q3,
      max,
      iqr,
      whiskerLow,
      whiskerHigh,
      outliers,
    });
  }

  teams.sort(
    (a, b) =>
      b.median - a.median || a.ownerUsername.localeCompare(b.ownerUsername),
  );

  const globalMin = teams.length ? Math.min(...teams.map((t) => t.min)) : 0;
  const globalMax = teams.length ? Math.max(...teams.map((t) => t.max)) : 0;

  return { teams, globalMin, globalMax };
}
