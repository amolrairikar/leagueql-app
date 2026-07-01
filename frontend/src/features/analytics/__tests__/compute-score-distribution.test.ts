import { describe, expect, it } from 'vitest';

import {
  computeScoreDistribution,
  gaussianKde,
  quantile,
} from '../compute-score-distribution';

import type { MatchupItem } from '@/components/api/types';

const NAMES: Record<string, string> = {
  T1: 'Alice',
  T2: 'Bob',
  T3: 'Cara',
  T4: 'Dan',
};

/** Minimal matchup between two teams in a given week (regular season by default). */
function game(
  week: string,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  tier = 'NONE',
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: NAMES[aId],
    team_a_team_name: `Team ${NAMES[aId]}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: [],
    team_a_bench: [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: NAMES[bId],
    team_b_team_name: `Team ${NAMES[bId]}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week,
    season: '2024',
  };
}

describe('quantile (linear interpolation, type 7)', () => {
  it('returns the value for a single-element array', () => {
    expect(quantile([42], 0.25)).toBe(42);
    expect(quantile([42], 0.5)).toBe(42);
  });

  it('matches d3/numpy quartiles on an evenly spaced array', () => {
    const s = [10, 20, 30, 40, 50];
    expect(quantile(s, 0.25)).toBe(20);
    expect(quantile(s, 0.5)).toBe(30);
    expect(quantile(s, 0.75)).toBe(40);
  });

  it('interpolates between points when the index is fractional', () => {
    const s = [50, 90, 100, 110, 120, 200];
    expect(quantile(s, 0.25)).toBeCloseTo(92.5);
    expect(quantile(s, 0.75)).toBeCloseTo(117.5);
  });
});

describe('gaussianKde', () => {
  it('is a normalized density that peaks at the data and integrates to ~1', () => {
    const grid = Array.from({ length: 201 }, (_, i) => -10 + i * 0.1); // -10..10
    const density = gaussianKde([0], 1, grid);
    // Symmetric single-point kernel peaks at the sample.
    const peakIdx = density.indexOf(Math.max(...density));
    expect(grid[peakIdx]).toBeCloseTo(0, 1);
    // Riemann sum over the grid approximates a probability density (area ~1).
    const area = density.reduce((a, d) => a + d * 0.1, 0);
    expect(area).toBeCloseTo(1, 1);
  });

  it('is bimodal for two well-separated clusters', () => {
    const grid = Array.from({ length: 201 }, (_, i) => -10 + i * 0.1);
    const density = gaussianKde([-5, 5], 1, grid);
    const at = (v: number) => density[Math.round((v + 10) / 0.1)];
    // Higher near each cluster than in the empty middle.
    expect(at(-5)).toBeGreaterThan(at(0));
    expect(at(5)).toBeGreaterThan(at(0));
  });
});

describe('computeScoreDistribution', () => {
  it('builds the five-number summary and mean from a manager regular-season scores', () => {
    // T1 scores: 10, 20, 30, 40, 50 across five weeks.
    const matchups = [
      game('1', 'T1', 10, 'T2', 5),
      game('2', 'T1', 20, 'T2', 5),
      game('3', 'T1', 30, 'T2', 5),
      game('4', 'T1', 40, 'T2', 5),
      game('5', 'T1', 50, 'T2', 5),
    ];
    const { teams } = computeScoreDistribution(matchups);
    const t1 = teams.find((t) => t.teamId === 'T1')!;
    expect(t1.scores).toEqual([10, 20, 30, 40, 50]);
    expect(t1.min).toBe(10);
    expect(t1.q1).toBe(20);
    expect(t1.median).toBe(30);
    expect(t1.q3).toBe(40);
    expect(t1.max).toBe(50);
    expect(t1.mean).toBe(30);
    expect(t1.iqr).toBe(20);
    // Sample (n-1) stdev of 10,20,30,40,50 → sqrt(1000/4).
    expect(t1.stdev).toBeCloseTo(15.811);
  });

  it('samples a density curve on the shared grid, peaking near the scores', () => {
    const matchups = [
      game('1', 'T1', 90, 'T2', 5),
      game('2', 'T1', 100, 'T2', 5),
      game('3', 'T1', 110, 'T2', 5),
    ];
    const { teams, grid, maxDensity } = computeScoreDistribution(matchups);
    const t1 = teams.find((t) => t.teamId === 'T1')!;
    // One density sample per grid point, all finite and non-negative.
    expect(t1.density).toHaveLength(grid.length);
    expect(t1.density.every((d) => Number.isFinite(d) && d >= 0)).toBe(true);
    // The curve's own peak lands near the manager's central scores (~100).
    const peakX = grid[t1.density.indexOf(Math.max(...t1.density))];
    expect(peakX).toBeGreaterThan(90);
    expect(peakX).toBeLessThan(110);
    // The reported shared vertical scale matches the tallest sampled density.
    expect(maxDensity).toBeGreaterThanOrEqual(Math.max(...t1.density));
  });

  it('renders a degenerate (single-score / zero-variance) manager as a finite bump', () => {
    const matchups = [
      // T1 has a real spread; T2 scores the same value every week.
      game('1', 'T1', 80, 'T2', 100),
      game('2', 'T1', 120, 'T2', 100),
    ];
    const { teams } = computeScoreDistribution(matchups);
    const t2 = teams.find((t) => t.teamId === 'T2')!;
    expect(t2.iqr).toBe(0);
    // Fallback bandwidth keeps the density finite and positive, not collapsed.
    expect(t2.density.every((d) => Number.isFinite(d))).toBe(true);
    expect(Math.max(...t2.density)).toBeGreaterThan(0);
  });

  it('excludes playoff weeks from a distribution', () => {
    const matchups = [
      game('1', 'T1', 100, 'T2', 90),
      game('2', 'T1', 999, 'T2', 80, 'WINNERS_BRACKET'),
    ];
    const { teams } = computeScoreDistribution(matchups);
    const t1 = teams.find((t) => t.teamId === 'T1')!;
    expect(t1.scores).toEqual([100]);
    expect(t1.max).toBe(100);
  });

  it('skips byes (a side with no finite score) and self-matchup placeholders', () => {
    const bye = game('2', 'T1', 100, 'T2', Number.NaN);
    const selfMatchup = game('3', 'T1', 100, 'T1', 100);
    const matchups = [game('1', 'T1', 100, 'T2', 90), bye, selfMatchup];
    const { teams } = computeScoreDistribution(matchups);
    const t1 = teams.find((t) => t.teamId === 'T1')!;
    // Only the week-1 score counts; the bye and self-matchup rows are dropped.
    expect(t1.scores).toEqual([100]);
  });

  it('sorts managers by median desc, tie-broken on username', () => {
    const matchups = [
      // Medians: Cara 120, Alice & Bob tie at 100, Dan 80.
      game('1', 'T3', 120, 'T4', 80),
      game('2', 'T3', 120, 'T4', 80),
      game('1', 'T1', 100, 'T2', 100),
      game('2', 'T1', 100, 'T2', 100),
    ];
    const { teams } = computeScoreDistribution(matchups);
    expect(teams.map((t) => t.ownerUsername)).toEqual([
      'Cara',
      'Alice',
      'Bob',
      'Dan',
    ]);
  });

  it('reports the global score range for a shared x-scale', () => {
    const matchups = [game('1', 'T1', 130, 'T2', 70)];
    const { globalMin, globalMax } = computeScoreDistribution(matchups);
    expect(globalMin).toBe(70);
    expect(globalMax).toBe(130);
  });

  it('returns an empty result with a zeroed range for no matchups', () => {
    const result = computeScoreDistribution([]);
    expect(result.teams).toEqual([]);
    expect(result.globalMin).toBe(0);
    expect(result.globalMax).toBe(0);
    // No managers → the shared vertical scale falls back to 1 (never 0).
    expect(result.maxDensity).toBe(1);
  });
});
