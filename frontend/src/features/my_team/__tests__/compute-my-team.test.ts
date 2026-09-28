import { describe, expect, it } from 'vitest';

import {
  computeMyTeam,
  listSeasonTeams,
  longestWinStreak,
  resolveClaimedTeam,
  topDraftPicks,
  type InSeasonView,
  type MyTeamInput,
  type OffseasonView,
} from '../compute-my-team';

import type {
  LeagueSettingsItem,
  MatchupItem,
  PlayerStat,
} from '@/components/api/types';
import type { DraftPickItem } from '@/features/draft_grades/api-calls';
import { computeStartSitReport } from '@/features/lineup_efficiency/compute-lineup-efficiency';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import { buildMatchupPreview } from '@/features/matchups/compute-preview';
import {
  buildPredictorModel,
  computePlayoffOdds,
} from '@/features/playoff_race_predictor/compute-projection';

const SEASON = '2025';
const SETTINGS: LeagueSettingsItem = {
  season: SEASON,
  num_playoff_teams: 2,
  num_playoff_teams_assumed: false,
  playoff_week_start: 5,
  regular_season_weeks: 4,
};

function player(id: number, pos: string, pts: number): PlayerStat {
  return {
    player_id: id,
    full_name: `P${id}`,
    points_scored: pts,
    position: pos,
    fantasy_position: pos,
  };
}

interface GameOpts {
  season?: string;
  tier?: string;
  aOwner?: string;
  bOwner?: string;
  aLineup?: { starters: PlayerStat[]; bench: PlayerStat[] };
}

/** A matchup; 0–0 scores mean unplayed. Owner ids default to `owner-<teamId>`. */
function game(
  week: number,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  opts: GameOpts = {},
): MatchupItem {
  const { season = SEASON, tier = 'NONE' } = opts;
  return {
    team_a_id: aId,
    team_a_display_name: `user${aId}`,
    team_a_team_name: `Team ${aId}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: opts.aLineup?.starters ?? [],
    team_a_bench: opts.aLineup?.bench ?? [],
    team_a_primary_owner_id: opts.aOwner ?? `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: `user${bId}`,
    team_b_team_name: `Team ${bId}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: opts.bOwner ?? `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week: String(week),
    season,
  };
}

// Lineups for team 1: week 1 perfect, week 2 benches an 18-pt WR for a 6-pt one.
const W1_LINEUP = {
  starters: [player(1, 'QB', 20), player(2, 'WR', 15)],
  bench: [player(3, 'WR', 5)],
};
const W2_LINEUP = {
  starters: [player(1, 'QB', 22), player(2, 'WR', 6)],
  bench: [player(3, 'WR', 18)],
};

/** Weeks 1–2 played, weeks 3–4 unplayed; plus two 2024 meetings of 1 vs 4. */
function midSeason(): MatchupItem[] {
  return [
    game(1, '1', 120, '2', 100, { aLineup: W1_LINEUP }),
    game(1, '3', 90, '4', 110),
    game(2, '1', 128.4, '3', 112.9, { aLineup: W2_LINEUP }),
    game(2, '2', 95, '4', 105),
    game(3, '1', 0, '4', 0),
    game(3, '2', 0, '3', 0),
    game(4, '1', 0, '2', 0),
    game(4, '3', 0, '4', 0),
    // 2024 on the old platform: owner ids migrated to the current ones.
    game(3, '7', 131, '8', 104.2, {
      season: '2024',
      aOwner: 'old-1',
      bOwner: 'old-4',
    }),
    game(9, '8', 140, '7', 100, {
      season: '2024',
      aOwner: 'old-4',
      bOwner: 'old-1',
    }),
  ];
}

const MIGRATION = new Map([
  ['old-1', 'owner-1'],
  ['old-4', 'owner-4'],
]);

function pick(
  overall: number,
  teamId: string,
  vorp: number | null,
  extra: Partial<DraftPickItem> = {},
): DraftPickItem {
  return {
    overall_pick_number: overall,
    round: Math.ceil(overall / 4),
    round_pick_number: ((overall - 1) % 4) + 1,
    team_id: teamId,
    player_id: String(overall),
    player_name: `Player ${overall}`,
    position: vorp == null ? 'K' : 'RB',
    vorp,
    total_points: vorp == null ? 90 : 100 + vorp,
    is_auction: false,
    bid_amount: 0,
    ...extra,
  } as DraftPickItem;
}

const DRAFT = [
  pick(1, '1', 85.2),
  pick(5, '1', 40.1),
  pick(9, '1', 62.7),
  pick(13, '1', 12),
  pick(17, '1', null),
  pick(2, '2', 120),
];

function input(
  matchups: MatchupItem[],
  standings: ManagerStandingsItem[] = [],
  draftPicks: DraftPickItem[] = DRAFT,
): MyTeamInput {
  return {
    matchups,
    standings,
    migrationMapping: MIGRATION,
    settings: SETTINGS,
    season: SEASON,
    draftPicks,
  };
}

const season = (ms: MatchupItem[]) => ms.filter((m) => m.season === SEASON);
const oddsOf = (ms: MatchupItem[], id: string) =>
  computePlayoffOdds(buildPredictorModel(ms, SETTINGS, 'live'), {}).get(id);

describe('listSeasonTeams / resolveClaimedTeam', () => {
  it('lists the season teams ordered by team id', () => {
    const teams = listSeasonTeams(midSeason(), SEASON);
    expect(teams.map((t) => t.teamId)).toEqual(['1', '2', '3', '4']);
    expect(teams[0]).toMatchObject({ ownerId: 'owner-1', teamName: 'Team 1' });
  });

  it('matches a claim through the migration mapping', () => {
    const teams = listSeasonTeams(midSeason(), SEASON);
    expect(resolveClaimedTeam(teams, 'old-1', MIGRATION)?.teamId).toBe('1');
    expect(resolveClaimedTeam(teams, 'owner-2', MIGRATION)?.teamId).toBe('2');
    expect(resolveClaimedTeam(teams, 'nobody', MIGRATION)).toBeNull();
    expect(resolveClaimedTeam(teams, null, MIGRATION)).toBeNull();
  });
});

describe('topDraftPicks', () => {
  it('takes the team top three by VORP, ignoring null VORP and other teams', () => {
    const top = topDraftPicks(DRAFT, '1');
    expect(top.map((p) => p.vorp)).toEqual([85.2, 62.7, 40.1]);
    expect(top[0]).toMatchObject({
      playerName: 'Player 1',
      position: 'RB',
      round: 1,
      roundPick: 1,
      overallPick: 1,
      bid: null,
      totalPoints: 185.2,
    });
  });

  it('returns fewer than three when fewer picks have a VORP', () => {
    const picks = [pick(1, '1', 10), pick(5, '1', null), pick(9, '1', 5)];
    expect(topDraftPicks(picks, '1').map((p) => p.vorp)).toEqual([10, 5]);
  });

  it('is empty with no draft data', () => {
    expect(topDraftPicks([], '1')).toEqual([]);
  });

  it('reports the bid for an auction draft and names unnamed players', () => {
    const [top] = topDraftPicks(
      [
        pick(3, '1', 7, {
          is_auction: true,
          bid_amount: 42,
          player_name: null,
        }),
      ],
      '1',
    );
    expect(top).toMatchObject({ bid: 42, playerName: 'Player 3' });
  });

  it('breaks VORP ties by the earlier pick', () => {
    const top = topDraftPicks([pick(9, '1', 5), pick(1, '1', 5)], '1');
    expect(top.map((p) => p.overallPick)).toEqual([1, 9]);
  });
});

describe('longestWinStreak', () => {
  it('counts consecutive wins in week order, ended by a loss or a tie', () => {
    const ms = [
      game(4, '1', 100, '2', 90), // W (listed out of order)
      game(1, '1', 100, '2', 90), // W
      game(2, '1', 100, '3', 90), // W
      game(3, '1', 95, '4', 95), // T ends the run at 2
      game(5, '3', 80, '1', 120), // W (team 1 on side b)
      game(6, '1', 100, '4', 90), // W → run of 3 (wks 4–6)
      game(7, '1', 80, '2', 90), // L
      game(8, '1', 0, '3', 0), // unplayed, ignored
    ];
    expect(longestWinStreak(ms, '1')).toBe(3);
  });

  it('is zero without a win', () => {
    expect(longestWinStreak([game(1, '1', 80, '2', 90)], '1')).toBe(0);
    expect(longestWinStreak([], '1')).toBe(0);
  });
});

describe('computeMyTeam', () => {
  it('returns null when the claimed owner has no team this season', () => {
    expect(computeMyTeam(input(midSeason()), 'nobody')).toBeNull();
    expect(computeMyTeam(input(midSeason()), null)).toBeNull();
  });

  it('summarizes an in-progress season', () => {
    const view = computeMyTeam(input(midSeason()), 'owner-1') as InSeasonView;
    expect(view.kind).toBe('in-season');
    expect(view.currentWeek).toBe(3);
    expect(view.lastWeek).toBe(2);
    expect(view.lastWeekGame).toEqual({
      result: 'W',
      points: 128.4,
      oppPoints: 112.9,
      margin: expect.closeTo(15.5, 5),
    });
    expect(view.team).toMatchObject({ wins: 2, losses: 0, rank: 1 });
    expect(view.team.pf).toBeCloseTo(248.4, 5);
    expect(view.team.pa).toBeCloseTo(212.9, 5);
  });

  it('matches the predictor for odds and the rolled-back odds change', () => {
    const ms = midSeason();
    const view = computeMyTeam(input(ms), 'owner-1') as InSeasonView;
    const now = oddsOf(season(ms), '1')!;
    const before = oddsOf(
      season(ms).map((m) =>
        m.week === '2' ? { ...m, team_a_score: 0, team_b_score: 0 } : m,
      ),
      '1',
    )!;
    expect(view.playoffOdds).toBeCloseTo(now, 10);
    expect(view.playoffOddsChange).toBeCloseTo(now - before, 10);
  });

  it('matches the matchup preview and builds the head-to-head across migrations', () => {
    const ms = midSeason();
    const view = computeMyTeam(input(ms), 'owner-1') as InSeasonView;
    const preview = buildMatchupPreview(season(ms), '1', '4');
    const m = view.matchup!;
    expect(m.opponent.teamId).toBe('4');
    expect(m.projMine).toBe(preview.projA);
    expect(m.projOpp).toBe(preview.projB);
    expect(m.winProbMine).toBe(preview.winProbA);
    expect(m.winProbOpp).toBe(preview.winProbB);
    expect(m.h2h).toEqual({ wins: 1, losses: 1, ties: 0 });
    expect(m.lastMeeting).toMatchObject({
      season: '2024',
      week: 9,
      result: 'L',
      points: 100,
      oppPoints: 140,
    });
    expect(m.opponentLast3).toEqual(['W', 'W']);
  });

  it('computes season efficiency and last week bench points like the chip', () => {
    const view = computeMyTeam(input(midSeason()), 'owner-1') as InSeasonView;
    const r1 = computeStartSitReport(W1_LINEUP.starters, W1_LINEUP.bench);
    const r2 = computeStartSitReport(W2_LINEUP.starters, W2_LINEUP.bench);
    expect(view.efficiency.seasonPct).toBeCloseTo(
      (r1.actualPoints + r2.actualPoints) /
        (r1.optimalPoints + r2.optimalPoints),
      10,
    );
    expect(view.efficiency.lastWeekPointsLeft).toBe(r2.pointsLeft);
    expect(r2.pointsLeft).toBe(12);
  });

  it('includes the top draft picks in both views', () => {
    const inSeason = computeMyTeam(input(midSeason()), 'owner-1')!;
    expect(inSeason.topDraftPicks.map((p) => p.vorp)).toEqual([
      85.2, 62.7, 40.1,
    ]);
    const offseason = computeMyTeam(
      input([game(1, '1', 120, '2', 100)]),
      'owner-1',
    )!;
    expect(offseason.kind).toBe('offseason');
    expect(offseason.topDraftPicks).toHaveLength(3);
  });

  it('reports last week awards and the highest-score count', () => {
    const view = computeMyTeam(input(midSeason()), 'owner-1') as InSeasonView;
    expect(view.awards.lastWeek).toContain('Highest Score');
    expect(view.awards.highestScoreCount).toBe(2);
  });

  it('handles Week 1 before any game is played', () => {
    const ms = midSeason().map((m) =>
      m.season === SEASON ? { ...m, team_a_score: 0, team_b_score: 0 } : m,
    );
    const view = computeMyTeam(input(ms), 'owner-1') as InSeasonView;
    expect(view.currentWeek).toBe(1);
    expect(view.lastWeek).toBeNull();
    expect(view.lastWeekGame).toBeNull();
    expect(view.playoffOddsChange).toBeNull();
    expect(view.efficiency).toEqual({
      seasonPct: null,
      lastWeekPointsLeft: null,
    });
    expect(view.awards).toEqual({ lastWeek: [], highestScoreCount: 0 });
    expect(view.matchup?.winProbMine).toBe(0.5);
    expect(view.matchup?.projMine).toBeNull();
  });

  it('shows no matchup when the team has a bye in the current week', () => {
    const ms = midSeason().filter(
      (m) => !(m.week === '3' && m.team_a_id === '1'),
    );
    const view = computeMyTeam(input(ms), 'owner-1') as InSeasonView;
    expect(view.currentWeek).toBe(3);
    expect(view.matchup).toBeNull();
  });

  it('shows the final result in the offseason', () => {
    const ms = [
      game(1, '1', 120, '2', 100),
      game(1, '3', 90, '4', 110),
      game(5, '1', 130, '4', 90, { tier: 'WINNERS_BRACKET' }),
    ];
    const standings = [
      {
        season: SEASON,
        owner_id: 'owner-1',
        final_rank: 1,
        champion: 'Yes',
      } as ManagerStandingsItem,
    ];
    const view = computeMyTeam(
      input(ms, standings),
      'owner-1',
    ) as OffseasonView;
    expect(view.kind).toBe('offseason');
    expect(view.finalRank).toBe(1);
    expect(view.champion).toBe(true);
    // Week 1 regular-season win + week 5 playoff win.
    expect(view.longestWinStreak).toBe(2);
    expect(view.team).toMatchObject({ wins: 1, losses: 0 });
  });

  it('offseason without a standings row has no final rank', () => {
    const view = computeMyTeam(
      input([game(1, '1', 120, '2', 100)]),
      'owner-2',
    ) as OffseasonView;
    expect(view).toMatchObject({ finalRank: null, champion: false });
    // Team 2 lost its only game.
    expect(view.longestWinStreak).toBe(0);
  });
});
