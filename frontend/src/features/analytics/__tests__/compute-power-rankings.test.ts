import { describe, expect, it } from 'vitest';

import { computePowerRankings } from '../compute-power-rankings';

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

function finalScore(teams: { teamId: string; points: { score: number }[] }[]) {
  return new Map(
    teams.map((t) => [t.teamId, t.points[t.points.length - 1].score]),
  );
}

// eslint-disable-next-line no-secrets/no-secrets -- function name, not a secret
describe('computePowerRankings', () => {
  it('blends all-play, points-for, and form into a single per-week score', () => {
    // One week, four teams. Scores: T1 100, T2 90, T3 80, T4 70.
    // n = 4 so all-play win fraction (apf) = wins / 3.
    //   T1 apf 3/3=1, T2 2/3, T3 1/3, T4 0.
    // Single week ⇒ AP = FORM = 100·apf; PF = 100·score/100 (T1 is league best).
    //   score = 0.5·AP + 0.3·PF + 0.2·FORM = 0.7·(100·apf) + 0.3·(100·score/100)
    const { weeks, teams } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('1', 'T3', 80, 'T4', 70),
    ]);

    expect(weeks).toEqual([1]);
    const scores = finalScore(teams);
    expect(scores.get('T1')).toBeCloseTo(100, 5);
    expect(scores.get('T2')).toBeCloseTo(0.7 * (100 / 1.5) + 0.3 * 90, 5); // 73.667
    expect(scores.get('T3')).toBeCloseTo(0.7 * (100 / 3) + 0.3 * 80, 5); // 47.333
    expect(scores.get('T4')).toBeCloseTo(0.3 * 70, 5); // 21
  });

  it('translates each week of scores into 1-based ranks (1 = best)', () => {
    const { teams } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('1', 'T3', 80, 'T4', 70),
    ]);
    const rank = new Map(
      teams.map((t) => [t.teamId, t.points[t.points.length - 1].rank]),
    );
    expect(rank.get('T1')).toBe(1);
    expect(rank.get('T2')).toBe(2);
    expect(rank.get('T3')).toBe(3);
    expect(rank.get('T4')).toBe(4);
  });

  it('orders managers by latest rank, tie-broken on username', () => {
    const { teams } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('1', 'T3', 80, 'T4', 70),
    ]);
    expect(teams.map((t) => t.ownerUsername)).toEqual([
      'Alice',
      'Bob',
      'Cara',
      'Dan',
    ]);
  });

  it('accumulates a point per week for each manager as the season runs', () => {
    const { weeks, teams } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('2', 'T1', 80, 'T2', 120),
      game('3', 'T1', 110, 'T2', 95),
    ]);
    expect(weeks).toEqual([1, 2, 3]);
    for (const team of teams) {
      expect(team.points.map((p) => p.week)).toEqual([1, 2, 3]);
    }
    // Alice wins weeks 1 & 3, Bob wins week 2 — Alice leads after week 3.
    expect(teams[0].ownerUsername).toBe('Alice');
  });

  it('excludes playoff weeks from the trend', () => {
    const { weeks } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('2', 'T1', 999, 'T2', 80, 'WINNERS_BRACKET'),
    ]);
    // Only the regular-season week 1 contributes.
    expect(weeks).toEqual([1]);
  });

  it('skips byes (a side with no finite score) and self-matchup placeholders', () => {
    const { weeks, teams } = computePowerRankings([
      game('1', 'T1', 100, 'T2', 90),
      game('2', 'T1', 100, 'T2', Number.NaN), // bye
      game('3', 'T1', 100, 'T1', 100), // self-matchup placeholder
    ]);
    expect(weeks).toEqual([1]);
    for (const team of teams) {
      expect(team.points).toHaveLength(1);
    }
  });

  it('returns an empty result for no matchups', () => {
    expect(computePowerRankings([])).toEqual({ weeks: [], teams: [] });
  });
});
