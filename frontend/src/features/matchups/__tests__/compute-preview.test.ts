import { describe, expect, it } from 'vitest';

import { buildMatchupPreview } from '../compute-preview';

import type { MatchupItem, PlayerStat } from '@/components/api/types';

const NAMES: Record<string, string> = { T1: 'Alice', T2: 'Bob', T3: 'Cara' };

function starter(
  id: number,
  name: string,
  pos: string,
  pts: number,
): PlayerStat {
  return { player_id: id, full_name: name, points_scored: pts, position: pos };
}

/** A regular-season matchup between two teams in a given week. */
function game(
  week: string,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  opts: {
    aStarters?: PlayerStat[];
    bStarters?: PlayerStat[];
    tier?: string;
  } = {},
): MatchupItem {
  const { aStarters = [], bStarters = [], tier = 'NONE' } = opts;
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

// T1 beats T2 and T3; scores are the T1 vs T2 preview's inputs.
const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 120, 'T2', 100, {
    aStarters: [starter(1, 'QB One', 'QB', 30), starter(2, 'RB One', 'RB', 20)],
    bStarters: [starter(3, 'WR Two', 'WR', 18)],
  }),
  game('2', 'T1', 110, 'T3', 130),
  game('2', 'T2', 90, 'T3', 95),
  game('3', 'T1', 100, 'T2', 88, {
    aStarters: [starter(1, 'QB One', 'QB', 25)],
  }),
  // Unplayed current week (excluded from all derivations).
  game('4', 'T1', 0, 'T2', 0),
];

describe('buildMatchupPreview', () => {
  it('computes records, PF/PA, and highest score from played games only', () => {
    const { teamA, teamB } = buildMatchupPreview(MATCHUPS, 'T1', 'T2');

    // T1 played weeks 1,2,3 (not the 0-0 week 4): W over T2, L to T3, W over T2.
    expect(teamA.record).toBe('2-1-0');
    expect(teamA.wins).toBe(2);
    expect(teamA.losses).toBe(1);
    expect(teamA.highScore).toBe(120);
    expect(teamA.avgPf).toBeCloseTo((120 + 110 + 100) / 3, 5);
    expect(teamA.avgPa).toBeCloseTo((100 + 130 + 88) / 3, 5);

    // T2 played weeks 1,2,3: L, L, L.
    expect(teamB.record).toBe('0-3-0');
    expect(teamB.winPct).toBe(0);
  });

  it('lists recent form ascending by week with per-game results', () => {
    const { teamA } = buildMatchupPreview(MATCHUPS, 'T1', 'T2');
    expect(teamA.recentForm.map((g) => g.week)).toEqual([1, 2, 3]);
    expect(teamA.recentForm.map((g) => g.result)).toEqual(['W', 'L', 'W']);
  });

  it('aggregates top scorers across a team’s played starters, totals desc', () => {
    const { teamA } = buildMatchupPreview(MATCHUPS, 'T1', 'T2');
    const qb = teamA.topScorers.find((p) => p.playerId === 1);
    expect(qb).toBeDefined();
    expect(qb?.total).toBeCloseTo(55, 5); // 30 (wk1) + 25 (wk3)
    expect(qb?.games).toBe(2);
    // Highest total first.
    expect(teamA.topScorers[0].playerId).toBe(1);
  });

  it('produces a win probability that sums to 1 and a projected score', () => {
    const { winProbA, winProbB, projA } = buildMatchupPreview(
      MATCHUPS,
      'T1',
      'T2',
    );
    expect(winProbA + winProbB).toBeCloseTo(1, 6);
    // T1 outscores T2 on average, so it should be favored.
    expect(winProbA).toBeGreaterThan(0.5);
    expect(projA).toBeCloseTo((120 + 110 + 100) / 3, 5);
  });

  it('falls back to a coin flip with no played games (season start)', () => {
    const preview = buildMatchupPreview(
      [game('1', 'T1', 0, 'T2', 0)],
      'T1',
      'T2',
    );
    expect(preview.winProbA).toBe(0.5);
    expect(preview.winProbB).toBe(0.5);
    expect(preview.projA).toBeNull();
    expect(preview.teamA.record).toBe('0-0-0');
    expect(preview.teamA.recentForm).toEqual([]);
    expect(preview.teamA.topScorers).toEqual([]);
    expect(preview.leagueWeekly).toEqual([]);
  });

  it('excludes playoff games from the derivations', () => {
    const withPlayoff: MatchupItem[] = [
      ...MATCHUPS,
      game('15', 'T1', 140, 'T2', 130, { tier: 'WINNERS_BRACKET' }),
    ];
    const { teamA } = buildMatchupPreview(withPlayoff, 'T1', 'T2');
    // Still only the 3 regular-season played games — the playoff win is ignored.
    expect(teamA.record).toBe('2-1-0');
    expect(teamA.highScore).toBe(120);
  });
});
