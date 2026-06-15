import { describe, expect, it } from 'vitest';

import { computeScheduleSwap, formatRecord } from '../compute-schedule-swap';

import type { MatchupItem } from '@/components/api/types';

const NAMES: Record<string, string> = {
  T1: 'Alice',
  T2: 'Bob',
  T3: 'Cara',
  T4: 'Dan',
};

/** Minimal regular-season matchup between two teams in a given week. */
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

// Actual records: T1 2-0, T2 1-1, T3 1-1, T4 0-2.
const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 100, 'T2', 90),
  game('1', 'T3', 80, 'T4', 70),
  game('2', 'T1', 100, 'T3', 95),
  game('2', 'T2', 60, 'T4', 50),
];

describe('computeScheduleSwap', () => {
  it('orders teams by actual wins desc, then win%, then username', () => {
    const { teams } = computeScheduleSwap(MATCHUPS);
    expect(teams.map((t) => t.teamId)).toEqual(['T1', 'T2', 'T3', 'T4']);
  });

  it('reproduces each team’s actual record on the diagonal', () => {
    const { matrix } = computeScheduleSwap(MATCHUPS);
    expect(matrix.get('T1')!.get('T1')).toMatchObject({ wins: 2, losses: 0 });
    expect(matrix.get('T2')!.get('T2')).toMatchObject({ wins: 1, losses: 1 });
    expect(matrix.get('T4')!.get('T4')).toMatchObject({ wins: 0, losses: 2 });
  });

  it('computes a team’s record under another manager’s schedule', () => {
    const { matrix } = computeScheduleSwap(MATCHUPS);
    // T1 dominates every week, so under T4's schedule it still goes 2-0.
    expect(matrix.get('T1')!.get('T4')).toMatchObject({ wins: 2, losses: 0 });
    // T4 loses every week, so under T1's schedule it still goes 0-2.
    expect(matrix.get('T4')!.get('T1')).toMatchObject({ wins: 0, losses: 2 });
  });

  it('substitutes the schedule owner when the swap would pit a team against itself', () => {
    const { matrix } = computeScheduleSwap(MATCHUPS);
    // Using T1's schedule, week 1's opponent is T2 itself → T2 instead faces T1
    // (90 < 100, loss); week 2 it faces T3 (60 < 95, loss): 0-2.
    expect(matrix.get('T2')!.get('T1')).toMatchObject({
      wins: 0,
      losses: 2,
      ties: 0,
      games: 2,
    });
  });

  it('ignores playoff games', () => {
    const withPlayoff = [
      ...MATCHUPS,
      game('3', 'T1', 10, 'T2', 200, 'WINNERS_BRACKET'),
    ];
    const { matrix } = computeScheduleSwap(withPlayoff);
    // Playoff loss must not enter T1's actual (diagonal) record.
    expect(matrix.get('T1')!.get('T1')).toMatchObject({ wins: 2, games: 2 });
  });

  it('returns no teams when there are no regular-season games', () => {
    const { teams } = computeScheduleSwap([
      game('1', 'T1', 10, 'T2', 200, 'WINNERS_BRACKET'),
    ]);
    expect(teams).toHaveLength(0);
  });

  it('formats records with ties only when present', () => {
    expect(formatRecord({ wins: 3, losses: 1, ties: 0, games: 4 })).toBe('3-1');
    expect(formatRecord({ wins: 3, losses: 1, ties: 2, games: 6 })).toBe(
      '3-1-2',
    );
  });
});
