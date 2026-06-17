import { describe, expect, it } from 'vitest';

import { computeWeeklyAwards } from '../compute-awards';

import type { MatchupItem } from '@/components/api/types';

const NAMES: Record<string, string> = {
  T1: 'Alice',
  T2: 'Bob',
  T3: 'Cara',
  T4: 'Dan',
};

/** Minimal matchup between two teams in a given week. */
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

// Week 1: T1 120-90 T2, T3 100-99 T4.
// Week 2: T1 80-70 T3, T2 110-60 T4.
const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 120, 'T2', 90),
  game('1', 'T3', 100, 'T4', 99),
  game('2', 'T1', 80, 'T3', 70),
  game('2', 'T2', 110, 'T4', 60),
];

describe('computeWeeklyAwards', () => {
  it('defaults the active week to the latest week when no week is selected', () => {
    const data = computeWeeklyAwards(MATCHUPS, null);
    expect(data.weeks).toEqual([1, 2]);
    expect(data.activeWeek).toBe(2);
  });

  it('computes each award type for the active week', () => {
    const { awards } = computeWeeklyAwards(MATCHUPS, 1);
    // Week 1 scores: T1 120, T2 90, T3 100, T4 99.
    expect(awards.highest?.teamId).toBe('T1');
    expect(awards.highest?.statText).toBe('120.00 pts');
    expect(awards.lowest?.teamId).toBe('T2');
    // Margins: T1/T2 = 30 (blowout), T3/T4 = 1 (narrowest).
    expect(awards.blowout?.teamId).toBe('T1');
    expect(awards.blowout?.statText).toBe('Won by 30.00 pts');
    expect(awards.narrowest?.teamId).toBe('T3');
    expect(awards.narrowest?.statText).toBe('Won by 1.00 pts');
    // Losers: T2 (90), T4 (99) → best loss is T4.
    expect(awards.bestLoss?.teamId).toBe('T4');
    // Winners: T1 (120), T3 (100) → worst win is T3.
    expect(awards.worstWin?.teamId).toBe('T3');
  });

  it('accumulates per-award counts across weeks 1…activeWeek, sorted by manager name', () => {
    const { tally } = computeWeeklyAwards(MATCHUPS, 2);
    const byId = Object.fromEntries(tally.map((r) => [r.teamId, r]));
    // Week 1 awards: highest T1, lowest T2, blowout T1, narrowest T3, bestLoss T4, worstWin T3.
    // Week 2 awards: highest T2, lowest T4, blowout T2, narrowest T1, bestLoss T3, worstWin T1.
    expect(byId.T1.counts.highest).toBe(1);
    expect(byId.T1.counts.blowout).toBe(1);
    expect(byId.T1.counts.narrowest).toBe(1);
    expect(byId.T1.counts.worstWin).toBe(1);
    expect(byId.T2.counts.lowest).toBe(1);
    expect(byId.T3.counts.bestLoss).toBe(1);
    expect(byId.T4.counts.bestLoss).toBe(1);
    expect(byId.T4.counts.lowest).toBe(1);
    // Rows are sorted alphabetically by manager (Alice, Bob, Cara, Dan); counts
    // are not summed into a total since the awards mix good and bad outcomes.
    expect(tally.map((r) => r.teamId)).toEqual(['T1', 'T2', 'T3', 'T4']);
    expect(tally[0]).not.toHaveProperty('total');
  });

  it('only counts weeks up to the active week in the tally', () => {
    const { tally } = computeWeeklyAwards(MATCHUPS, 1);
    const awarded = tally.reduce(
      (sum, r) => sum + Object.values(r.counts).reduce((a, b) => a + b, 0),
      0,
    );
    // One winner per of the 6 award types in week 1 only.
    expect(awarded).toBe(6);
  });

  it('surfaces the longest active win streak (≥ 2) through the active week', () => {
    // T1 wins week 1 and week 2 → active streak of 2.
    const { longestStreak } = computeWeeklyAwards(MATCHUPS, 2);
    expect(longestStreak?.teamId).toBe('T1');
    expect(longestStreak?.length).toBe(2);
  });

  it('returns no streak when no team has won 2+ in a row through the week', () => {
    const { longestStreak } = computeWeeklyAwards(MATCHUPS, 1);
    expect(longestStreak).toBeNull();
  });

  it('breaks a streak when the most recent game is a loss', () => {
    const matchups = [
      game('1', 'T1', 120, 'T2', 90),
      game('2', 'T1', 100, 'T2', 80),
      game('3', 'T1', 50, 'T2', 130), // T1 loses, streak resets
    ];
    expect(computeWeeklyAwards(matchups, 3).longestStreak).toBeNull();
    // Through week 2, T1 had a 2-game streak.
    expect(computeWeeklyAwards(matchups, 2).longestStreak?.teamId).toBe('T1');
  });

  it('breaks award and winner/loser ties deterministically by username', () => {
    // Two teams tie for the highest score; Alice (T1) wins on localeCompare.
    const matchups = [
      game('1', 'T1', 100, 'T3', 80),
      game('1', 'T2', 100, 'T4', 70),
    ];
    expect(computeWeeklyAwards(matchups, 1).awards.highest?.teamId).toBe('T1');
  });

  it('excludes tied matchups from win/loss-based awards but not score awards', () => {
    const matchups = [game('1', 'T1', 90, 'T2', 90)];
    const { awards } = computeWeeklyAwards(matchups, 1);
    // Highest/lowest still resolve (tie broken by username → Alice both).
    expect(awards.highest?.teamId).toBe('T1');
    expect(awards.lowest?.teamId).toBe('T1');
    // No decided game → no blowout/narrowest/bestLoss/worstWin.
    expect(awards.blowout).toBeUndefined();
    expect(awards.narrowest).toBeUndefined();
    expect(awards.bestLoss).toBeUndefined();
    expect(awards.worstWin).toBeUndefined();
  });

  it('skips byes and self-matchup placeholders', () => {
    const matchups = [
      game('1', 'T1', 120, 'T2', 90),
      game('1', 'T3', 0, 'T3', 0), // self-matchup placeholder (bye)
    ];
    const { tally, awards } = computeWeeklyAwards(matchups, 1);
    // T3 never appears (its only row is a placeholder).
    expect(tally.map((r) => r.teamId)).toEqual(
      expect.not.arrayContaining(['T3']),
    );
    expect(awards.highest?.teamId).toBe('T1');
  });

  it('computes awards for playoff weeks too', () => {
    const matchups = [game('14', 'T1', 130, 'T2', 70, 'WINNERS_BRACKET')];
    const { awards, weeks } = computeWeeklyAwards(matchups, 14);
    expect(weeks).toEqual([14]);
    expect(awards.highest?.teamId).toBe('T1');
    expect(awards.blowout?.teamId).toBe('T1');
  });

  it('returns an empty tally when there is no matchup data', () => {
    const data = computeWeeklyAwards([], null);
    expect(data.tally).toEqual([]);
    expect(data.longestStreak).toBeNull();
    expect(data.awards).toEqual({});
  });
});
