import { describe, expect, it } from 'vitest';

import {
  buildPredictorModel,
  computeClinchScenarios,
  computePlayoffOdds,
  projectStandings,
  recordEnteringWeek,
  totalPickableMatchups,
  type Picks,
  type PredictorModel,
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

describe('computePlayoffOdds', () => {
  const sum = (odds: Map<string, number>) =>
    [...odds.values()].reduce((a, b) => a + b, 0);

  it('gives two otherwise-symmetric teams 50% each for one deciding game', () => {
    // One unplayed regular-season game, one playoff spot, no baseline edge.
    const model = buildPredictorModel(
      [game('t1', 't2', 1)],
      settings({ num_playoff_teams: 1, regular_season_weeks: 1 }),
      'live',
    );
    const odds = computePlayoffOdds(model, {});
    expect(odds.get('t1')).toBeCloseTo(0.5, 10);
    expect(odds.get('t2')).toBeCloseTo(0.5, 10);
  });

  it('reads 100% for a clinched team and 0% for eliminated teams', () => {
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
    const odds = computePlayoffOdds(model, {});
    expect(odds.get('t1')).toBe(1); // 5-0, cannot be caught
    expect(odds.get('t2')).toBe(0);
    expect(odds.get('t3')).toBe(0);
  });

  it('always keeps exactly num_playoff_teams worth of odds in play', () => {
    // Every outcome seats exactly N teams, so the odds sum to N regardless.
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    expect(sum(computePlayoffOdds(model, {}))).toBeCloseTo(2, 10);
  });

  it('is conditional on picks: locking in a team lifts it to 100%', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    const base = computePlayoffOdds(model, {});
    // t1 is 2-0 but not yet clinched (t2 and t3 can each reach 3 wins).
    expect(base.get('t1')!).toBeLessThan(1);
    expect(base.get('t1')!).toBeGreaterThan(0.5);
    // Win both remaining games and t1 is locked into the top seed.
    const picks: Picks = { '3:0': 't1', '4:0': 't1' };
    expect(computePlayoffOdds(model, picks).get('t1')).toBe(1);
  });

  it('is deterministic (0/1) once every matchup is picked', () => {
    const model = buildPredictorModel(liveMatchups(), settings(), 'live');
    const picks: Picks = {
      '3:0': 't1',
      '3:1': 't3',
      '4:0': 't1',
      '4:1': 't2',
    };
    const odds = computePlayoffOdds(model, picks);
    for (const v of odds.values()) expect(v === 0 || v === 1).toBe(true);
    expect(sum(odds)).toBeCloseTo(2, 10);
  });

  it('falls back to seeded sampling for a large outcome space', () => {
    // 6 teams over 8 unplayed weeks = 24 free matchups (> the exact cap),
    // forcing the Monte Carlo path.
    const teams = ['t1', 't2', 't3', 't4', 't5', 't6'];
    const matchups: MatchupItem[] = [];
    for (let week = 1; week <= 8; week++) {
      matchups.push(game(teams[0], teams[1], week));
      matchups.push(game(teams[2], teams[3], week));
      matchups.push(game(teams[4], teams[5], week));
    }
    const model = buildPredictorModel(
      matchups,
      settings({ num_playoff_teams: 4, regular_season_weeks: 8 }),
      'live',
    );
    expect(totalPickableMatchups(model)).toBe(24);
    const first = computePlayoffOdds(model, {});
    const second = computePlayoffOdds(model, {});
    // Seeded RNG => identical results across runs.
    expect([...second.entries()]).toEqual([...first.entries()]);
    // Sampled or not, odds stay in range and sum to the number of seeds.
    for (const v of first.values()) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
    expect(sum(first)).toBeCloseTo(4, 10);
  });
});

describe('settings fallbacks', () => {
  it('defaults to 6 assumed playoff teams when settings are absent', () => {
    const model = buildPredictorModel(liveMatchups(), null, 'live');
    expect(model.numPlayoffTeams).toBe(6);
    expect(model.numPlayoffTeamsAssumed).toBe(true);
  });
});

/** Build a PredictorModel directly, to control win totals and points-for exactly. */
function mkModel(
  teams: { id: string; wins: number; pf: number }[],
  weeks: { week: number; games: [string, string][] }[],
  numPlayoffTeams: number,
): PredictorModel {
  return {
    teams: new Map(
      teams.map((t) => [
        t.id,
        {
          teamId: t.id,
          ownerUsername: `owner-${t.id}`,
          teamName: t.id,
          teamLogo: null,
        },
      ]),
    ),
    baseline: new Map(
      teams.map((t) => [t.id, { wins: t.wins, losses: 0, ties: 0, pf: t.pf }]),
    ),
    weeks: weeks.map((w) => ({
      week: w.week,
      matchups: w.games.map(([a, b], i) => ({
        key: `${w.week}:${i}`,
        week: w.week,
        teamAId: a,
        teamBId: b,
      })),
    })),
    numPlayoffTeams,
    numPlayoffTeamsAssumed: false,
    regularSeasonWeeks: Math.max(...weeks.map((w) => w.week)),
    hasPlayedPlayoffMatchup: false,
  };
}

describe('computeClinchScenarios', () => {
  // Verified final-week cluster (see scratchpad/rigorous.mjs): top 6 of 10.
  // Sharks/Foxes/Bears clinch by record; Colts/Mules/Newts are out by record; the
  // four 8-5 teams each "win & in" with a loss-branch points-for tiebreak.
  const clusterModel = () =>
    mkModel(
      [
        { id: 'Sharks', wins: 12, pf: 1720 },
        { id: 'Foxes', wins: 11, pf: 1665 },
        { id: 'Bears', wins: 10, pf: 1600 },
        { id: 'Wolves', wins: 8, pf: 1540 },
        { id: 'Hawks', wins: 8, pf: 1525 },
        { id: 'Rams', wins: 8, pf: 1510 },
        { id: 'Owls', wins: 8, pf: 1500 },
        { id: 'Colts', wins: 6, pf: 1450 },
        { id: 'Mules', wins: 4, pf: 1370 },
        { id: 'Newts', wins: 3, pf: 1300 },
      ],
      [
        {
          week: 14,
          games: [
            ['Sharks', 'Newts'],
            ['Foxes', 'Mules'],
            ['Bears', 'Colts'],
            ['Wolves', 'Hawks'],
            ['Rams', 'Owls'],
          ],
        },
      ],
      6,
    );

  it('lists only contending teams; clinched and eliminated are excluded', () => {
    const res = computeClinchScenarios(clusterModel(), {})!;
    expect(res).not.toBeNull();
    expect(res.scenarios.map((s) => s.team.teamId)).toEqual([
      'Wolves',
      'Hawks',
      'Rams',
      'Owls',
    ]);
    expect(res.scenarios.every((s) => s.category === 'win-and-in')).toBe(true);
  });

  it('attaches the points-for margin for a loss-branch tie', () => {
    const res = computeClinchScenarios(clusterModel(), {})!;
    const wolves = res.scenarios.find((s) => s.team.teamId === 'Wolves')!;
    expect(wolves.opponent!.teamId).toBe('Hawks');
    expect(wolves.tieMargins.map((m) => [m.rival.teamId, m.gap])).toEqual([
      ['Rams', 30],
      ['Owls', 40],
    ]);
    const owls = res.scenarios.find((s) => s.team.teamId === 'Owls')!;
    expect(owls.tieMargins.map((m) => [m.rival.teamId, m.gap])).toEqual([
      ['Wolves', -40],
      ['Hawks', -25],
    ]);
  });

  it('detects controls-its-own-destiny (win in, lose out) with no tie margin', () => {
    // top 2 of 4: A clinched, D eliminated, B vs C a play-in for seed 2.
    const model = mkModel(
      [
        { id: 'A', wins: 3, pf: 300 },
        { id: 'B', wins: 2, pf: 260 },
        { id: 'C', wins: 2, pf: 250 },
        { id: 'D', wins: 0, pf: 150 },
      ],
      [
        {
          week: 2,
          games: [
            ['A', 'D'],
            ['B', 'C'],
          ],
        },
      ],
      2,
    );
    const res = computeClinchScenarios(model, {})!;
    const ids = res.scenarios.map((s) => s.team.teamId);
    expect(ids).toContain('B');
    expect(ids).toContain('C');
    expect(ids).not.toContain('A'); // clinched by record
    expect(ids).not.toContain('D'); // eliminated
    const b = res.scenarios.find((s) => s.team.teamId === 'B')!;
    expect(b.category).toBe('controls-destiny');
    expect(b.tieMargins).toEqual([]);
  });

  it('detects must-win with the win-branch tiebreak margin', () => {
    // top 1 of 4: A/B/C each must win, and even a win only ties for the seat.
    const model = mkModel(
      [
        { id: 'A', wins: 2, pf: 250 },
        { id: 'B', wins: 2, pf: 240 },
        { id: 'C', wins: 2, pf: 230 },
        { id: 'D', wins: 1, pf: 200 },
      ],
      [
        {
          week: 2,
          games: [
            ['A', 'D'],
            ['B', 'C'],
          ],
        },
      ],
      1,
    );
    const res = computeClinchScenarios(model, {})!;
    const a = res.scenarios.find((s) => s.team.teamId === 'A')!;
    expect(a.category).toBe('must-win');
    expect(a.opponent!.teamId).toBe('D');
    expect(a.tieMargins.map((m) => [m.rival.teamId, m.gap])).toEqual([
      ['B', 10],
      ['C', 20],
    ]);
  });

  it('returns null when the outcome space is too large to enumerate', () => {
    const teams = ['t1', 't2', 't3', 't4', 't5', 't6'];
    const matchups: MatchupItem[] = [];
    for (let week = 1; week <= 8; week++) {
      matchups.push(game(teams[0], teams[1], week));
      matchups.push(game(teams[2], teams[3], week));
      matchups.push(game(teams[4], teams[5], week));
    }
    const model = buildPredictorModel(
      matchups,
      settings({ num_playoff_teams: 4, regular_season_weeks: 8 }),
      'live',
    );
    expect(computeClinchScenarios(model, {})).toBeNull();
  });

  it('returns null when nothing is decisive yet', () => {
    // 4 teams, top 2, two full weeks left, no baseline edge.
    const model = mkModel(
      [
        { id: 'A', wins: 0, pf: 0 },
        { id: 'B', wins: 0, pf: 0 },
        { id: 'C', wins: 0, pf: 0 },
        { id: 'D', wins: 0, pf: 0 },
      ],
      [
        {
          week: 1,
          games: [
            ['A', 'B'],
            ['C', 'D'],
          ],
        },
        {
          week: 2,
          games: [
            ['A', 'C'],
            ['B', 'D'],
          ],
        },
      ],
      2,
    );
    expect(computeClinchScenarios(model, {})).toBeNull();
  });

  it('is conditional on picks: a pick narrows who is still fighting', () => {
    const model = mkModel(
      [
        { id: 'A', wins: 2, pf: 250 },
        { id: 'B', wins: 2, pf: 240 },
        { id: 'C', wins: 2, pf: 230 },
        { id: 'D', wins: 1, pf: 200 },
      ],
      [
        {
          week: 2,
          games: [
            ['A', 'D'],
            ['B', 'C'],
          ],
        },
      ],
      1,
    );
    const before = computeClinchScenarios(model, {})!;
    expect(before.scenarios.map((s) => s.team.teamId).sort()).toEqual([
      'A',
      'B',
      'C',
    ]);
    // Lock in B over C: C's game is decided (and lost), so only A is still fighting,
    // now needing only to hold off B on the tiebreak.
    const after = computeClinchScenarios(model, { '2:1': 'B' })!;
    expect(after.scenarios.map((s) => s.team.teamId)).toEqual(['A']);
    const a = after.scenarios[0];
    expect(a.category).toBe('must-win');
    expect(a.tieMargins.map((m) => [m.rival.teamId, m.gap])).toEqual([
      ['B', 10],
    ]);
  });
});
