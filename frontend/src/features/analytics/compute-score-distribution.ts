import type { MatchupItem } from '@/components/api/types';

/** Number of x-samples the shared density grid is evaluated on. */
const GRID_SIZE = 80;

/** A manager's ridgeline (joy-plot) stats over their regular-season weekly scores. */
export interface RidgeStats {
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
  mean: number;
  iqr: number;
  /** Sample standard deviation of `scores`, or 0 for a single score. */
  stdev: number;
  /** Gaussian-KDE density sampled at each x in the shared {@link ScoreDistributionData.grid}. */
  density: number[];
}

export interface ScoreDistributionData {
  /** Managers sorted by median desc, tie-broken on username. */
  teams: RidgeStats[];
  /** Smallest score across all managers (for a shared x-scale), or 0 when empty. */
  globalMin: number;
  /** Largest score across all managers (for a shared x-scale), or 0 when empty. */
  globalMax: number;
  /** Shared x-grid every manager's `density` is sampled on (ascending). */
  grid: number[];
  /** Largest density value across all managers, for a shared vertical scale (at least 1). */
  maxDensity: number;
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
 * Gaussian kernel-density estimate of `sorted` evaluated at each point in `grid`.
 * Returns a proper density (integrates to ~1 over the real line).
 */
export function gaussianKde(
  sorted: number[],
  bandwidth: number,
  grid: number[],
): number[] {
  const n = sorted.length;
  const norm = 1 / (n * bandwidth * Math.sqrt(2 * Math.PI));
  return grid.map((gx) => {
    let sum = 0;
    for (const s of sorted) {
      const u = (gx - s) / bandwidth;
      sum += Math.exp(-0.5 * u * u);
    }
    return sum * norm;
  });
}

/** Sample (n-1) standard deviation, or 0 for fewer than two values. */
export function sampleStdev(values: number[]): number {
  const n = values.length;
  if (n < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const variance = values.reduce((a, s) => a + (s - mean) ** 2, 0) / (n - 1);
  return Math.sqrt(variance);
}

/**
 * Silverman's rule-of-thumb bandwidth, `0.9 * min(stdev, iqr/1.349) * n^(-1/5)`.
 * Falls back to `fallback` (a small fraction of the global range) when the sample
 * is degenerate — a single score or zero spread — so the ridge still renders.
 */
function bandwidthFor(
  sorted: number[],
  stdev: number,
  iqr: number,
  fallback: number,
): number {
  const n = sorted.length;
  if (n < 2) return fallback;
  const spread = iqr > 0 ? Math.min(stdev, iqr / 1.349) : stdev;
  const bw = 0.9 * spread * Math.pow(n, -1 / 5);
  return bw > 0 ? bw : fallback;
}

/**
 * Build per-manager weekly-score ridgeline stats from a season's matchups (FE-033).
 *
 * Each matchup contributes its two scored sides as (team, score) points. Only
 * regular-season games count; byes (a side with no finite score) and self-matchup
 * placeholders (`team_a_id === team_b_id`) are skipped. Quartiles use linear
 * interpolation; each manager's distribution is smoothed into a Gaussian KDE curve
 * sampled on a shared x-grid so the ridges are directly comparable. Managers are
 * sorted by median desc, tie-broken on username.
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

  // First pass: five-number summary + mean for each manager.
  const teams: RidgeStats[] = [];
  for (const [id, raw] of scoresByTeam) {
    const scores = [...raw].sort((a, b) => a - b);
    const q1 = quantile(scores, 0.25);
    const q3 = quantile(scores, 0.75);
    teams.push({
      ...meta.get(id)!,
      scores,
      min: scores[0],
      q1,
      median: quantile(scores, 0.5),
      q3,
      max: scores[scores.length - 1],
      mean: scores.reduce((a, b) => a + b, 0) / scores.length,
      iqr: q3 - q1,
      stdev: sampleStdev(scores),
      density: [], // filled below, once the shared grid is known
    });
  }

  teams.sort(
    (a, b) =>
      b.median - a.median || a.ownerUsername.localeCompare(b.ownerUsername),
  );

  const globalMin = teams.length ? Math.min(...teams.map((t) => t.min)) : 0;
  const globalMax = teams.length ? Math.max(...teams.map((t) => t.max)) : 0;

  // Shared x-grid spanning the padded global range, plus a degenerate-sample
  // bandwidth fallback keyed to that range.
  const range = globalMax - globalMin || 1;
  const lo = globalMin - range * 0.05;
  const hi = globalMax + range * 0.05;
  const grid = Array.from(
    { length: GRID_SIZE },
    (_, i) => lo + ((hi - lo) * i) / (GRID_SIZE - 1),
  );
  const fallbackBw = range * 0.03;

  // Second pass: sample each manager's KDE onto the shared grid.
  let maxDensity = 0;
  for (const t of teams) {
    const bw = bandwidthFor(t.scores, t.stdev, t.iqr, fallbackBw);
    t.density = gaussianKde(t.scores, bw, grid);
    for (const d of t.density) if (d > maxDensity) maxDensity = d;
  }

  return {
    teams,
    globalMin,
    globalMax,
    grid,
    maxDensity: maxDensity || 1,
  };
}
