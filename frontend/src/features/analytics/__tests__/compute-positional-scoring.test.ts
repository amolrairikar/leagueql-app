import { describe, expect, it } from 'vitest';

import { computePositionalScoring } from '../compute-positional-scoring';

import type { MatchupItem, PlayerStat } from '@/components/api/types';

const NAMES: Record<string, string> = {
  T1: 'Alice',
  T2: 'Bob',
  T3: 'Cara',
};

function starter(
  position: string,
  points: number,
  fantasy_position?: string,
): PlayerStat {
  return {
    player_id: Math.floor(Math.random() * 1e6),
    full_name: `${position} player`,
    points_scored: points,
    position,
    fantasy_position: fantasy_position ?? position,
  };
}

/** Minimal matchup with per-side starter lists (regular season by default). */
function game(
  week: string,
  aId: string,
  aScore: number,
  aStarters: PlayerStat[],
  bId: string,
  bScore: number,
  bStarters: PlayerStat[],
  tier = 'NONE',
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: NAMES[aId],
    team_a_team_name: `Team ${NAMES[aId]}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: aStarters,
    team_a_bench: [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: NAMES[bId],
    team_b_team_name: `Team ${NAMES[bId]}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: bStarters,
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

describe('computePositionalScoring', () => {
  it('sums starter points per real position for each manager', () => {
    const { positions, teams } = computePositionalScoring([
      game('1', 'T1', 100, [starter('QB', 25), starter('RB', 15)], 'T2', 90, [
        starter('WR', 20),
      ]),
    ]);

    expect(positions).toEqual(['QB', 'RB', 'WR']);
    const byName = new Map(teams.map((t) => [t.ownerUsername, t]));
    expect(byName.get('Alice')!.byPosition).toEqual({ QB: 25, RB: 15 });
    expect(byName.get('Alice')!.total).toBe(40);
    expect(byName.get('Bob')!.byPosition).toEqual({ WR: 20 });
  });

  it('rolls FLEX/superflex points into the real position', () => {
    const { teams } = computePositionalScoring([
      game(
        '1',
        'T1',
        50,
        [starter('RB', 10, 'RB'), starter('WR', 8, 'FLEX')],
        'T2',
        40,
        [starter('QB', 30, 'SUPER_FLEX')],
      ),
    ]);
    const byName = new Map(teams.map((t) => [t.ownerUsername, t]));
    // The FLEX'd WR lands in WR, not a FLEX bucket; the superflex QB lands in QB.
    expect(byName.get('Alice')!.byPosition).toEqual({ RB: 10, WR: 8 });
    expect(byName.get('Bob')!.byPosition).toEqual({ QB: 30 });
  });

  it('normalizes D/ST to DEF', () => {
    const { positions, teams } = computePositionalScoring([
      game('1', 'T1', 10, [starter('D/ST', 9)], 'T2', 5, [starter('K', 5)]),
    ]);
    expect(positions).toEqual(['DEF', 'K']);
    const byName = new Map(teams.map((t) => [t.ownerUsername, t]));
    expect(byName.get('Alice')!.byPosition).toEqual({ DEF: 9 });
  });

  it('groups positions without a dedicated color under "Other"', () => {
    const { positions, teams } = computePositionalScoring([
      game('1', 'T1', 20, [starter('LB', 7), starter('DB', 5)], 'T2', 10, [
        starter('QB', 10),
      ]),
    ]);
    expect(positions).toEqual(['QB', 'Other']);
    const byName = new Map(teams.map((t) => [t.ownerUsername, t]));
    expect(byName.get('Alice')!.byPosition).toEqual({ Other: 12 });
  });

  it('excludes playoff weeks (regular season only)', () => {
    const { teams } = computePositionalScoring([
      game('1', 'T1', 100, [starter('QB', 20)], 'T2', 90, [starter('QB', 18)]),
      game(
        '2',
        'T1',
        110,
        [starter('QB', 30)],
        'T2',
        80,
        [starter('QB', 12)],
        'WINNERS_BRACKET',
      ),
    ]);
    const alice = teams.find((t) => t.ownerUsername === 'Alice')!;
    // Only the regular-season week contributes; the playoff week is excluded.
    expect(alice.byPosition).toEqual({ QB: 20 });
  });

  it('skips byes (a side with no finite score) and self-matchup placeholders', () => {
    const { teams } = computePositionalScoring([
      game('1', 'T1', 100, [starter('QB', 20)], 'T2', 90, [starter('QB', 18)]),
      // Bye: Bob's side has no finite score, so his starters here are ignored.
      game('2', 'T1', 100, [starter('QB', 5)], 'T2', Number.NaN, [
        starter('QB', 99),
      ]),
      // Self-matchup placeholder: skipped entirely.
      game('3', 'T1', 100, [starter('QB', 99)], 'T1', 100, [starter('QB', 99)]),
    ]);
    const byName = new Map(teams.map((t) => [t.ownerUsername, t]));
    expect(byName.get('Alice')!.byPosition).toEqual({ QB: 25 });
    expect(byName.get('Bob')!.byPosition).toEqual({ QB: 18 });
  });

  it('treats non-finite player points as 0', () => {
    const { teams } = computePositionalScoring([
      game(
        '1',
        'T1',
        20,
        [starter('QB', Number.NaN), starter('RB', 10)],
        'T2',
        10,
        [starter('QB', 10)],
      ),
    ]);
    const alice = teams.find((t) => t.ownerUsername === 'Alice')!;
    expect(alice.byPosition).toEqual({ QB: 0, RB: 10 });
    expect(alice.total).toBe(10);
  });

  it('orders managers by total points descending, tie-broken on username', () => {
    const { teams } = computePositionalScoring([
      // Equal totals (30 each) → alphabetical: Bob before Cara.
      game('1', 'T2', 30, [starter('QB', 30)], 'T3', 30, [starter('QB', 30)]),
      // Alice tops them with 40.
      game('1', 'T1', 40, [starter('QB', 40)], 'T2', 0, [starter('QB', 0)]),
    ]);
    expect(teams.map((t) => t.ownerUsername)).toEqual(['Alice', 'Bob', 'Cara']);
  });

  it('returns an empty result for no matchups', () => {
    expect(computePositionalScoring([])).toEqual({ positions: [], teams: [] });
  });
});
