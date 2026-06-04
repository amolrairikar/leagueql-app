/**
 * Shared response fixtures for component tests.
 *
 * Keyed by the `queryType` base the MSW `leagueQuery` helper switches on
 * (`SEASON_STANDINGS`, `MATCHUPS`, `WEEKLY_STANDINGS`, `PLAYOFF_BRACKET`,
 * `DRAFT`). Small but shaped like the real precomputed views so each analytics
 * page renders real values.
 */

export const LEAGUE = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const starters = (a: string, b: string) => [
  {
    player_id: 'p1',
    full_name: a,
    points_scored: 30,
    position: 'QB',
    fantasy_position: 'QB',
  },
  {
    player_id: 'p2',
    full_name: b,
    points_scored: 20,
    position: 'RB',
    fantasy_position: 'RB',
  },
];

export const STANDINGS = [
  {
    season: '2024',
    team_id: '1',
    owner_id: 'uA',
    team_name: 'Team Alice',
    team_logo: null,
    owner_username: 'Alice',
    final_rank: 1,
    games_played: 1,
    wins: 1,
    losses: 0,
    ties: 0,
    record: '1-0-0',
    win_pct: 1,
    total_pf: 130,
    total_pa: 120,
    avg_pf: 130,
    avg_pa: 120,
    total_vs_league_wins: 1,
    total_vs_league_losses: 0,
    win_pct_vs_league: 1,
    champion: 'Yes',
  },
  {
    season: '2024',
    team_id: '2',
    owner_id: 'uB',
    team_name: 'Team Bob',
    team_logo: null,
    owner_username: 'Bob',
    final_rank: 2,
    games_played: 1,
    wins: 0,
    losses: 1,
    ties: 0,
    record: '0-1-0',
    win_pct: 0,
    total_pf: 120,
    total_pa: 130,
    avg_pf: 120,
    avg_pa: 130,
    total_vs_league_wins: 0,
    total_vs_league_losses: 1,
    win_pct_vs_league: 0,
    champion: 'No',
  },
];

export const MATCHUPS = [
  {
    season: '2024',
    week: '1',
    team_a_id: '1',
    team_a_display_name: 'Alice',
    team_a_team_name: 'Team Alice',
    team_a_team_logo: null,
    team_a_primary_owner_id: 'uA',
    team_a_secondary_owner_id: null,
    team_a_score: 130,
    team_a_starters: starters('Pat Quarterback', 'Run Back'),
    team_a_bench: [
      {
        player_id: 'p3',
        full_name: 'Wide Receiver',
        points_scored: 10,
        position: 'WR',
      },
    ],
    team_b_id: '2',
    team_b_display_name: 'Bob',
    team_b_team_name: 'Team Bob',
    team_b_team_logo: null,
    team_b_primary_owner_id: 'uB',
    team_b_secondary_owner_id: null,
    team_b_score: 120,
    team_b_starters: starters('Quincy Back', 'Tight Endzone'),
    team_b_bench: [
      {
        player_id: 'p6',
        full_name: 'Kicker Kid',
        points_scored: 8,
        position: 'K',
      },
    ],
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: '1',
    loser: '2',
  },
];

export const WEEKLY_STANDINGS = [
  {
    season: '2024',
    snapshot_week: '1',
    team_id: '1',
    owner_id: 'uA',
    owner_username: 'Alice',
    games_played: 1,
    wins: 1,
    losses: 0,
    ties: 0,
    record: '1-0-0',
  },
  {
    season: '2024',
    snapshot_week: '1',
    team_id: '2',
    owner_id: 'uB',
    owner_username: 'Bob',
    games_played: 1,
    wins: 0,
    losses: 1,
    ties: 0,
    record: '0-1-0',
  },
];

export const PLAYOFF_BRACKET = [
  {
    match_id: 1,
    round: 1,
    team_1_id: '1',
    team_1_display_name: 'Alice',
    team_1_team_name: 'Team Alice',
    team_1_team_logo: null,
    team_2_id: '2',
    team_2_display_name: 'Bob',
    team_2_team_name: 'Team Bob',
    team_2_team_logo: null,
    winner: '1',
    loser: '2',
    position: 1,
    team_1_from: null,
    team_2_from: null,
    season: '2024',
    team_1_score: 130,
    team_2_score: 120,
  },
];

export const DRAFT = [
  {
    actual_position_rank: 1,
    auto_draft_type_id: 0,
    bid_amount: 0,
    drafted_position_rank: 1,
    draft_rank_delta: 0,
    is_auction: false,
    keeper: false,
    lineup_slot_id: 0,
    member_id: 'uA',
    nominating_team_id: 0,
    overall_pick_number: 1,
    owner_username: 'Alice',
    pick_id: 1,
    player_id: 'p1',
    player_name: 'Pat Quarterback',
    position: 'QB',
    reserved_for_keeper: false,
    round: 1,
    round_pick_number: 1,
    season: '2024',
    team_id: '1',
    team_logo: '',
    team_name: 'Team Alice',
    total_points: 300,
    trade_locked: false,
    vorp: 50,
  },
];
