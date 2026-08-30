/** Test factories for the My Team compute modules. */
import type { TeamMetrics } from '../compute-team-metrics';

import type {
  MatchupItem,
  PlayerStat,
  SeasonStandingsItem,
} from '@/components/api/types';
import type { DraftPickItem } from '@/features/draft_grades/api-calls';

export function draftPick(
  overrides: Partial<DraftPickItem> = {},
): DraftPickItem {
  return {
    actual_position_rank: null,
    auto_draft_type_id: 0,
    bid_amount: 0,
    drafted_position_rank: 0,
    draft_rank_delta: null,
    is_auction: false,
    keeper: false,
    lineup_slot_id: 0,
    member_id: 'm',
    nominating_team_id: 0,
    overall_pick_number: 1,
    owner_username: 'mgr1',
    pick_id: 1,
    player_id: 'p',
    player_name: 'Player',
    position: 'RB',
    reserved_for_keeper: false,
    round: 1,
    round_pick_number: 1,
    season: '2024',
    team_id: 't1',
    team_logo: '',
    team_name: 'Team 1',
    total_points: 100,
    trade_locked: false,
    vorp: null,
    ...overrides,
  };
}

export function player(
  id: number,
  points: number,
  position = 'RB',
  fantasyPosition = position,
): PlayerStat {
  return {
    player_id: id,
    full_name: `Player ${id}`,
    points_scored: points,
    position,
    fantasy_position: fantasyPosition,
  };
}

interface GameOpts {
  week?: number;
  tier?: string;
  aStarters?: PlayerStat[];
  aBench?: PlayerStat[];
  bStarters?: PlayerStat[];
  bBench?: PlayerStat[];
}

/** A played matchup between two teams with the given scores. */
export function game(
  aId: string,
  bId: string,
  aScore: number,
  bScore: number,
  opts: GameOpts = {},
): MatchupItem {
  const { week = 1, tier = 'NONE' } = opts;
  return {
    team_a_id: aId,
    team_a_display_name: `mgr${aId}`,
    team_a_team_name: `Team ${aId}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: opts.aStarters ?? [],
    team_a_bench: opts.aBench ?? [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: `mgr${bId}`,
    team_b_team_name: `Team ${bId}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: opts.bStarters ?? [],
    team_b_bench: opts.bBench ?? [],
    team_b_primary_owner_id: `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week: String(week),
    season: '2024',
  };
}

export function standing(
  overrides: Partial<SeasonStandingsItem> & { team_id: string },
): SeasonStandingsItem {
  return {
    season: '2024',
    owner_id: `owner-${overrides.team_id}`,
    team_name: `Team ${overrides.team_id}`,
    team_logo: '',
    owner_username: `mgr${overrides.team_id}`,
    games_played: 10,
    wins: 5,
    losses: 5,
    ties: 0,
    record: '5-5',
    win_pct: 0.5,
    total_vs_league_wins: 45,
    total_vs_league_losses: 45,
    win_pct_vs_league: 0.5,
    total_pf: 1000,
    total_pa: 1000,
    avg_pf: 100,
    avg_pa: 100,
    champion: 'No',
    ...overrides,
  };
}

/** A neutral TeamMetrics baseline; override fields to trigger specific insights. */
export function baseMetrics(overrides: Partial<TeamMetrics> = {}): TeamMetrics {
  return {
    teamId: 't1',
    ownerUsername: 'mgr1',
    teamName: 'Team 1',
    teamLogo: null,
    numTeams: 12,
    wins: 6,
    losses: 5,
    ties: 0,
    record: '6-5',
    winPct: 0.545,
    gamesPlayed: 11,
    seed: 6,
    totalPf: 1200,
    avgPf: 109,
    pfRank: 6,
    allPlayWins: 60,
    allPlayLosses: 60,
    allPlayWinPct: 0.5,
    expectedWins: 6,
    luck: 0,
    sos: 0.5,
    sosRank: 6,
    efficiency: 0.96,
    pointsLeft: 40,
    worstBenchWeek: null,
    powerRank: null,
    grade: null,
    draft: {
      bestPick: null,
      worstPick: null,
      steals: 0,
      busts: 0,
      scorablePicks: [],
    },
    recentForm: [],
    trades: { best: null, worst: null, tradeCount: 0, waiverCount: 0 },
    platform: 'SLEEPER',
    hasTransactions: false,
    ...overrides,
  };
}
