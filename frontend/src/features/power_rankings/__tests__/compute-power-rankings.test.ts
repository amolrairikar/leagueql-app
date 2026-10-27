import { describe, expect, it } from 'vitest';

import {
  buildPowerRankings,
  POWER_COMPONENTS,
} from '../compute-power-rankings';

import type { MatchupItem, PlayerStat } from '@/components/api/types';

const NAMES: Record<string, string> = {
  '1': 'Amy',
  '2': 'Ben',
  '3': 'Cal',
  '4': 'Dee',
};

const qb = (id: number, pts: number): PlayerStat => ({
  player_id: id,
  full_name: `QB ${id}`,
  points_scored: pts,
  position: 'QB',
  fantasy_position: 'QB',
});

interface GameOptions {
  tier?: string;
  aStarters?: PlayerStat[];
  aBench?: PlayerStat[];
  bStarters?: PlayerStat[];
  bBench?: PlayerStat[];
}

function game(
  week: number,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  options: GameOptions = {},
): MatchupItem {
  return {
    season: '2024',
    week: String(week),
    team_a_id: aId,
    team_a_display_name: NAMES[aId] ?? `M${aId}`,
    team_a_team_name: `Team ${NAMES[aId] ?? aId}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: options.aStarters ?? [],
    team_a_bench: options.aBench ?? [],
    team_a_primary_owner_id: `u${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: NAMES[bId] ?? `M${bId}`,
    team_b_team_name: `Team ${NAMES[bId] ?? bId}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: options.bStarters ?? [],
    team_b_bench: options.bBench ?? [],
    team_b_primary_owner_id: `u${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: options.tier ?? 'NONE',
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
  };
}

// Amy wins every week and scores the most; Dee loses every week and scores the least.
const SEASON: MatchupItem[] = [
  game(1, '1', 150, '2', 100),
  game(1, '3', 120, '4', 80),
  game(2, '1', 140, '3', 110),
  game(2, '2', 90, '4', 70),
  game(3, '1', 160, '4', 60),
  game(3, '2', 100, '3', 105),
];

describe('buildPowerRankings', () => {
  it('weights the four components to 100', () => {
    expect(POWER_COMPONENTS.reduce((sum, c) => sum + c.weight, 0)).toBe(100);
  });

  it('ranks teams by power score with the strongest team first', () => {
    const rows = buildPowerRankings(SEASON).through(3);
    expect(rows.map((r) => r.managerName)).toEqual([
      'Amy',
      'Cal',
      'Ben',
      'Dee',
    ]);
    expect(rows.map((r) => r.rank)).toEqual([1, 2, 3, 4]);
    expect(rows[0].record).toBe('3-0');
    expect(rows[0].teamName).toBe('Team Amy');
    expect(rows[0].score).toBeGreaterThan(rows[1].score);
  });

  it('only offers played regular-season weeks', () => {
    const rankings = buildPowerRankings([
      ...SEASON,
      game(4, '1', 0, '2', 0), // unplayed placeholder
      game(15, '1', 300, '2', 10, { tier: 'WINNERS_BRACKET' }), // postseason
    ]);
    expect(rankings.playedWeeks).toEqual([1, 2, 3]);
    expect(rankings.through(4)).toEqual([]);
    expect(rankings.through(15)).toEqual([]);
  });

  it('does not let placeholder or playoff games change the scores', () => {
    const clean = buildPowerRankings(SEASON).through(3);
    const noisy = buildPowerRankings([
      ...SEASON,
      game(4, '1', 0, '2', 0),
      game(15, '4', 500, '1', 1, { tier: 'WINNERS_BRACKET' }),
    ]).through(3);
    expect(noisy.map((r) => [r.teamId, r.record, r.score])).toEqual(
      clean.map((r) => [r.teamId, r.record, r.score]),
    );
  });

  it('returns no rankings for a season with no played games', () => {
    const rankings = buildPowerRankings([game(1, '1', 0, '2', 0)]);
    expect(rankings.playedWeeks).toEqual([]);
    expect(rankings.through(1)).toEqual([]);
  });

  it('uses only games through the requested week', () => {
    const rows = buildPowerRankings(SEASON).through(1);
    expect(rows).toHaveLength(4);
    expect(rows.find((r) => r.managerName === 'Dee')?.record).toBe('0-1');
    expect(rows.find((r) => r.managerName === 'Amy')?.record).toBe('1-0');
  });

  it('shows no movement at the earliest week', () => {
    const rows = buildPowerRankings(SEASON).through(1);
    for (const row of rows) {
      expect(row.prevRank).toBeNull();
      expect(row.movement).toBe(0);
      expect(row.trend).toEqual([row.rank]);
    }
  });

  it('reports movement as previous rank minus current rank', () => {
    // Ben leads after week 1; Amy overtakes him with a huge week 2.
    const rankings = buildPowerRankings([
      game(1, '1', 90, '2', 100),
      game(2, '1', 200, '2', 100),
    ]);
    const week1 = rankings.through(1);
    expect(week1[0].managerName).toBe('Ben');
    const amy = rankings.through(2).find((r) => r.managerName === 'Amy')!;
    expect(amy.rank).toBe(1);
    expect(amy.prevRank).toBe(2);
    expect(amy.movement).toBe(1);
    expect(amy.trend).toEqual([2, 1]);
  });

  it('keeps ranks, movement, trend and verdicts internally consistent', () => {
    // Deterministic pseudo-random 8-team, 9-week season.
    let seed = 7;
    const next = () => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed / 2147483648;
    };
    const matchups: MatchupItem[] = [];
    for (let week = 1; week <= 9; week++) {
      const order = ['1', '2', '3', '4', '5', '6', '7', '8'].sort(
        () => next() - 0.5,
      );
      for (let i = 0; i < order.length; i += 2) {
        matchups.push(
          game(
            week,
            order[i],
            Math.round(70 + next() * 80),
            order[i + 1],
            Math.round(70 + next() * 80),
          ),
        );
      }
    }
    const rankings = buildPowerRankings(matchups);
    expect(rankings.playedWeeks).toHaveLength(9);

    for (const week of rankings.playedWeeks) {
      const rows = rankings.through(week);
      expect(rows.map((r) => r.rank)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
      expect(rows.map((r) => r.recordRank).sort()).toEqual([
        1, 2, 3, 4, 5, 6, 7, 8,
      ]);
      for (const row of rows) {
        expect(row.trend.length).toBeLessThanOrEqual(6);
        expect(row.trend[row.trend.length - 1]).toBe(row.rank);
        if (row.prevRank !== null) {
          expect(row.movement).toBe(row.prevRank - row.rank);
        }
        const gap = row.recordRank - row.rank;
        expect(row.verdict).toBe(
          gap >= 2 ? 'underrated' : gap <= -2 ? 'overrated' : 'on-the-mark',
        );
        expect(row.score).toBeGreaterThanOrEqual(0);
        expect(row.score).toBeLessThanOrEqual(100);
      }
    }
    // A six-week trend window slides rather than growing.
    expect(rankings.through(9)[0].trend).toHaveLength(6);
  });

  it('scores every team 50 on a scaled component when all are equal', () => {
    const rows = buildPowerRankings([game(1, '1', 100, '2', 100)]).through(1);
    for (const row of rows) {
      expect(row.record).toBe('0-0-1');
      expect(row.components.find((c) => c.key === 'points')?.value).toBe(50);
      expect(row.components.find((c) => c.key === 'record')?.value).toBe(50);
      expect(row.score).toBe(50);
    }
  });

  it('formats the expected record from the schedule-swap expected wins', () => {
    const rows = buildPowerRankings([
      game(1, '1', 90, '2', 100),
      game(2, '1', 200, '2', 100),
    ]).through(2);
    for (const row of rows) {
      expect(row.expectedWins).toBeCloseTo(1);
      expect(row.expectedRecord).toBe('1.0-1.0');
    }
  });

  describe('lineup efficiency', () => {
    it('is unavailable, and left out of the score, without bench data', () => {
      const rows = buildPowerRankings(SEASON).through(3);
      for (const row of rows) {
        const efficiency = row.components.find((c) => c.key === 'efficiency')!;
        expect(efficiency.value).toBeNull();
        expect(efficiency.delta).toBeNull();
      }
      // With efficiency unavailable the score is the weighted average of the other three.
      const amy = rows[0];
      const rest = amy.components.filter((c) => c.value !== null);
      const total = rest.reduce((s, c) => s + c.value! * c.weight, 0);
      const weight = rest.reduce((s, c) => s + c.weight, 0);
      expect(rest).toHaveLength(3);
      expect(amy.score).toBeCloseTo(total / weight);
    });

    it('scores the manager who started the better lineup higher', () => {
      // Amy benched a 30-point QB for a 20-point one; Ben started his best QB.
      const rows = buildPowerRankings([
        game(1, '1', 100, '2', 100, {
          aStarters: [qb(1, 20)],
          aBench: [qb(2, 30)],
          bStarters: [qb(3, 30)],
          bBench: [qb(4, 10)],
        }),
      ]).through(1);
      const eff = (name: string) =>
        rows
          .find((r) => r.managerName === name)!
          .components.find((c) => c.key === 'efficiency')!.value;
      expect(eff('Ben')).toBe(100);
      expect(eff('Amy')).toBe(0);
    });

    it('counts a team with no bench data only on the components it has', () => {
      const rows = buildPowerRankings([
        game(1, '1', 100, '2', 100, {
          aStarters: [qb(1, 20)],
          aBench: [qb(2, 30)],
        }),
      ]).through(1);
      const ben = rows.find((r) => r.managerName === 'Ben')!;
      expect(
        ben.components.find((c) => c.key === 'efficiency')?.value,
      ).toBeNull();
      expect(Number.isFinite(ben.score)).toBe(true);
    });
  });

  it('writes a blurb naming the strongest and weakest areas', () => {
    const [top] = buildPowerRankings(SEASON).through(3);
    expect(top.blurb).toMatch(/Strongest area: .+\. Weakest: .+\./);
  });
});
