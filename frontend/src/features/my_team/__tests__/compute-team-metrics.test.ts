import { describe, expect, it } from 'vitest';

import { computeTeamMetrics } from '../compute-team-metrics';

import { draftPick, game, player, standing } from './factories';

import type { TransactionItem } from '@/components/api/types';
import { buildWeeklyPlayerPoints } from '@/features/transactions/api-calls';

const standings = [
  standing({
    team_id: 't1',
    wins: 2,
    losses: 1,
    record: '2-1',
    win_pct: 0.667,
    total_pf: 340,
  }),
  standing({
    team_id: 't2',
    wins: 1,
    losses: 2,
    record: '1-2',
    win_pct: 0.333,
    total_pf: 290,
  }),
  standing({
    team_id: 't3',
    wins: 0,
    losses: 3,
    record: '0-3',
    win_pct: 0,
    total_pf: 240,
  }),
];

// t1: W (wk1), L (wk2), W (wk3). Week 1 gives t1 bench data with points left.
const matchups = [
  game('t1', 't2', 110, 90, {
    week: 1,
    aStarters: [player(1, 10, 'RB')],
    aBench: [player(2, 30, 'RB')],
  }),
  game('t1', 't3', 100, 120, { week: 2 }),
  game('t1', 't2', 130, 100, { week: 3 }),
];

const draftPicks = [
  draftPick({
    team_id: 't1',
    player_name: 'Steal',
    draft_rank_delta: 12,
    actual_position_rank: 6,
    round: 3,
  }),
  draftPick({
    team_id: 't1',
    player_name: 'Bust',
    draft_rank_delta: -8,
    round: 2,
  }),
];

const trades: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'tx1',
    type: 'trade',
    week: 1,
    created: 0,
    roster_ids: ['t1', 't2'],
    teams: [
      { roster_id: 't1', team_name: 'Team t1', display_name: 'mgrt1' },
      { roster_id: 't2', team_name: 'Team t2', display_name: 'mgrt2' },
    ],
    adds: [
      {
        player_id: '99',
        player_name: 'NewGuy',
        position: 'WR',
        roster_id: 't1',
      },
      {
        player_id: '88',
        player_name: 'OldGuy',
        position: 'WR',
        roster_id: 't2',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  },
  {
    season: '2024',
    transaction_id: 'wx1',
    type: 'waiver',
    week: 2,
    created: 0,
    roster_ids: ['t1'],
    teams: [{ roster_id: 't1', team_name: 'Team t1', display_name: 'mgrt1' }],
    adds: [
      {
        player_id: '77',
        player_name: 'Pickup',
        position: 'RB',
        roster_id: 't1',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: 20,
  },
];

const input = {
  teamId: 't1',
  platform: 'SLEEPER' as const,
  standings,
  matchups,
  draftPicks,
  transactions: trades,
  weekly: buildWeeklyPlayerPoints(matchups),
};

describe('compute-team-metrics', () => {
  it('returns null when the team is not in the standings', () => {
    expect(computeTeamMetrics({ ...input, teamId: 'nope' })).toBeNull();
  });

  it('computes seed and points-for rank from the standings', () => {
    const m = computeTeamMetrics(input)!;
    expect(m.seed).toBe(1);
    expect(m.pfRank).toBe(1);
    expect(m.numTeams).toBe(3);
    expect(m.record).toBe('2-1');
  });

  it('builds recent form newest-first with the right opponent and result', () => {
    const m = computeTeamMetrics(input)!;
    expect(m.recentForm[0]).toMatchObject({
      week: 3,
      result: 'W',
      opponent: 'mgrt2',
    });
    expect(m.recentForm[1]).toMatchObject({
      week: 2,
      result: 'L',
      opponent: 'mgrt3',
    });
    expect(m.recentForm[2]).toMatchObject({ week: 1, result: 'W' });
  });

  it('aggregates lineup efficiency and points left over weeks with bench data', () => {
    const m = computeTeamMetrics(input)!;
    // Week 1: started 10, optimal 30 → 20 left; other weeks have no bench data.
    expect(m.pointsLeft).toBeCloseTo(20, 5);
    expect(m.efficiency).toBeCloseTo(10 / 30, 5);
  });

  it('grades the draft and surfaces best/worst picks', () => {
    const m = computeTeamMetrics(input)!;
    expect(m.draft.bestPick?.player_name).toBe('Steal');
    expect(m.draft.worstPick?.player_name).toBe('Bust');
  });

  it('counts trades and waivers for the team', () => {
    const m = computeTeamMetrics(input)!;
    expect(m.trades.tradeCount).toBe(1);
    expect(m.trades.waiverCount).toBe(1);
    expect(m.trades.best?.acquired).toContain('NewGuy');
    expect(m.hasTransactions).toBe(true);
  });

  it('produces a power rank and a grade for the team', () => {
    const m = computeTeamMetrics(input)!;
    expect(m.powerRank?.teamId).toBe('t1');
    expect(m.grade?.letter).toBeTruthy();
  });
});
