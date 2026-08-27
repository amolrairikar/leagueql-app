import { describe, expect, it } from 'vitest';

import {
  buildPredictorModel,
  projectStandings,
  recordEnteringWeek,
  totalPickableMatchups,
  type Picks,
} from '../compute-projection';

import type { LeagueSettingsItem, MatchupItem } from '@/components/api/types';

/** A matchup between two teams in a given week; 0-0 scores mean unplayed. */
function game(
  aId: string,
  bId: string,
  week: number,
  aScore = 0,
  bScore = 0,
  tier = 'NONE',
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: `owner-${aId}`,
    team_a_team_name: `Team ${aId}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: [],
    team_a_bench: [],
    team_a_primary_owner_id: `pid-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: `owner-${bId}`,
    team_b_team_name: `Team ${bId}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: `pid-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: tier === 'NONE' ? null : 'Finals',
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week: String(week),
    season: '2024',
  };
}

function settings(
  overrides: Partial<LeagueSettingsItem> = {},
): LeagueSettingsItem {
  return {
    season: '2024',
    num_playoff_teams: 2,
    num_playoff_teams_assumed: false,
    playoff_week_start: 5,
    regular_season_weeks: 4,
    ...overrides,
  };
}

/**
 * A 4-team season: weeks 1-2 played, weeks 3-4 are unplayed (0-0) placeholders.
 * Baseline after wk1-2: t1 2-0 (pf 200), t3 1-1 (190), t2 1-1 (180), t4 0-2 (160).
 */
function liveMatchups(): MatchupItem[] {
  return [
    game('t1', 't2', 1, 100, 90),
    game('t3', 't4', 1, 100, 80),
    game('t1', 't3', 2, 100, 90),
    game('t2', 't4', 2, 100, 80),
    game('t1', 't2', 3),
    game('t3', 't4', 3),
    game('t1', 't3', 4),
    game('t2', 't4', 4),
  ];
}

describe('buildPredictorModel (live)', () => {
  it('makes only the unplayed regular-season weeks pickable', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    expect(model.weeks.map((w) => w.week)).toEqual([3, 4]);
    expect(totalPickableMatchups(model)).toBe(4);
    expect(model.hasPlayedPlayoffMatchup).toBe(false);
  });

  it('computes the baseline from played games only', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    expect(model.baseline.get('t1')).toEqual({
      wins: 2,
      losses: 0,
      ties: 0,
      pf: 200,
    });
    expect(model.baseline.get('t4')).toEqual({
      wins: 0,
      losses: 2,
      ties: 0,
      pf: 160,
    });
  });

  it('excludes played playoff games and never makes them pickable', () => {
    const matchups = [
      ...liveMatchups(),
      game('t1', 't2', 5, 120, 110, 'WINNERS_BRACKET'),
    ];
    const model = buildPredictorModel(matchups, settings(), 'live');
    expect(model.hasPlayedPlayoffMatchup).toBe(true);
    expect(model.weeks.map((w) => w.week)).toEqual([3, 4]);
    // The playoff game does not inflate anyone's projected record.
    const rows = projectStandings(model, {});
    expect(rows.find((r) => r.team.teamId === 't1')!.wins).toBe(2);
  });
});

describe('projectStandings', () => {
  it('seeds by wins then points-for with the playoff cutoff', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    const rows = projectStandings(model, {});
    // t2 and t3 both sit at 1-1 with 190 PF, so the team-id tiebreak orders t2 first.
    expect(rows.map((r) => r.team.teamId)).toEqual(['t1', 't2', 't3', 't4']);
    expect(rows[0]).toMatchObject({ seed: 1, inPlayoffs: true });
    expect(rows[1]).toMatchObject({ seed: 2, inPlayoffs: true });
    expect(rows[2].inPlayoffs).toBe(false);
  });

  it('re-sorts and reports movement when picks change the order', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    // t3 wins both remaining games (over t4 in wk3, over t1 in wk4) -> 3 wins,
    // climbing from seed 3 to the top seed and pushing t2 out of the top 2.
    const picks: Picks = { '3:1': 't3', '4:0': 't3' };
    const rows = projectStandings(model, picks);
    const t3 = rows.find((r) => r.team.teamId === 't3')!;
    expect(t3.seed).toBe(1);
    expect(t3.wins).toBe(3);
    expect(t3.movement).toBe(2); // baseline seed 3 -> projected seed 1
    const t2 = rows.find((r) => r.team.teamId === 't2')!;
    expect(t2.inPlayoffs).toBe(false);
    expect(t2.movement).toBeLessThan(0);
  });

  it('marks a team clinched only while games remain unpicked', () => {
    const matchups = [
      game('t1', 't2', 1, 100, 50),
      game('t1', 't3', 2, 100, 50),
      game('t1', 't2', 3, 100, 50),
      game('t1', 't3', 4, 100, 50),
      game('t1', 't2', 5, 100, 50),
      game('t2', 't3', 6), // the only unplayed (pickable) game
    ];
    const model = buildPredictorModel(
      matchups,
      settings({ num_playoff_teams: 1, regular_season_weeks: 6 }),
      'live',
    );
    // t1 (5-0) cannot be caught by t2/t3 who can reach at most 2 wins.
    const before = projectStandings(model, {});
    expect(before.find((r) => r.team.teamId === 't1')!.clinched).toBe(true);
    // Once every game is picked, the clinched badge drops (standings are final).
    const after = projectStandings(model, { '6:0': 't2' });
    expect(after.find((r) => r.team.teamId === 't1')!.clinched).toBe(false);
  });
});

describe('recordEnteringWeek', () => {
  it('includes earlier-week picks but not the current week', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    const picks: Picks = { '3:0': 't2', '4:1': 't2' };
    // Entering week 3, t2 has only its baseline 1-1.
    expect(recordEnteringWeek(model, 't2', 3, picks)).toMatchObject({
      wins: 1,
      losses: 1,
    });
    // Entering week 4, t2's week-3 win is included -> 2-1.
    expect(recordEnteringWeek(model, 't2', 4, picks)).toMatchObject({
      wins: 2,
      losses: 1,
    });
  });
});

describe('buildPredictorModel (replay)', () => {
  it('replays the last three regular-season weeks over a completed season', () => {
    const completed: MatchupItem[] = [];
    // 5 fully-played weeks, t1 wins everything.
    for (let week = 1; week <= 5; week++) {
      completed.push(game('t1', 't2', week, 100, 50));
      completed.push(game('t3', 't4', week, 90, 80));
    }
    const model = buildPredictorModel(
      completed,
      settings({ regular_season_weeks: 5, playoff_week_start: 6 }),
      'replay',
    );
    expect(model.weeks.map((w) => w.week)).toEqual([3, 4, 5]);
    // Baseline is only weeks 1-2, so t1 has 2 wins entering the window (not 5).
    expect(model.baseline.get('t1')!.wins).toBe(2);
  });
});

describe('settings fallbacks', () => {
  it('defaults to 6 assumed playoff teams when settings are absent', () => {
    const model = buildPredictorModel(liveMatchups(), null, 'live');
    expect(model.numPlayoffTeams).toBe(6);
    expect(model.numPlayoffTeamsAssumed).toBe(true);
  });
});
