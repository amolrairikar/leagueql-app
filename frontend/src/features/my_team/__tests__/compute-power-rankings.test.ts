import { describe, expect, it } from 'vitest';

import { computePowerRankings } from '../compute-power-rankings';

import { game } from './factories';

describe('compute-power-rankings', () => {
  it('ranks the higher-scoring team ahead and covers every team once', () => {
    const matchups = [
      game('1', '2', 130, 90, { week: 1 }),
      game('1', '2', 125, 95, { week: 2 }),
    ];
    const ranks = computePowerRankings(matchups);
    expect(ranks.map((r) => r.teamId)).toEqual(['1', '2']);
    expect(ranks[0].rank).toBe(1);
    expect(ranks[1].rank).toBe(2);
  });

  it('reports week-over-week movement vs the prior week', () => {
    // Through week 1: team 2 leads. Week 2: team 1 blows out and overtakes.
    const matchups = [
      game('1', '2', 80, 140, { week: 1 }),
      game('3', '4', 100, 90, { week: 1 }),
      game('1', '2', 200, 70, { week: 2 }),
      game('3', '4', 100, 95, { week: 2 }),
    ];
    const ranks = computePowerRankings(matchups);
    const team1 = ranks.find((r) => r.teamId === '1')!;
    // Team 1 climbed from the bottom after the week-2 explosion → positive movement.
    expect(team1.movement).toBeGreaterThan(0);
    expect(team1.previousRank).not.toBeNull();
  });

  it('returns an empty ranking when there are no played games', () => {
    expect(computePowerRankings([])).toEqual([]);
  });

  it('ignores playoff and unplayed games', () => {
    const matchups = [
      game('1', '2', 100, 90, { week: 1 }),
      game('1', '2', 0, 0, { week: 2 }), // unplayed placeholder
      game('1', '2', 50, 200, { week: 3, tier: 'WINNERS_BRACKET' }), // playoff
    ];
    const ranks = computePowerRankings(matchups);
    // Only the regular-season week-1 game counts, so team 1 stays ahead.
    expect(ranks[0].teamId).toBe('1');
  });
});
