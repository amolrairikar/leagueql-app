import { describe, expect, it } from 'vitest';

import { computeStrengthOfSchedule } from '../compute-sos';

import type { MatchupItem, SeasonStandingsItem } from '@/components/api/types';

/** A standings row carrying just the fields the SoS helper reads. */
function standing(
  teamId: string,
  winPct: number,
): Pick<SeasonStandingsItem, 'team_id' | 'win_pct'> {
  return { team_id: teamId, win_pct: winPct };
}

/** Minimal matchup between two teams in a given week. */
function game(aId: string, bId: string, tier = 'NONE'): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: aId,
    team_a_team_name: `Team ${aId}`,
    team_a_team_logo: null,
    team_a_score: 0,
    team_a_starters: [],
    team_a_bench: [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: bId,
    team_b_team_name: `Team ${bId}`,
    team_b_team_logo: null,
    team_b_score: 0,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: null,
    winner: aId,
    loser: bId,
    week: '1',
    season: '2024',
  };
}

const standings = [
  standing('1', 1),
  standing('2', 0.5),
  standing('3', 0),
] as SeasonStandingsItem[];

describe('computeStrengthOfSchedule', () => {
  it('averages the win% of every opponent faced', () => {
    // Team 1 faces team 2 (0.5) and team 3 (0) -> avg 0.25.
    const sos = computeStrengthOfSchedule(standings, [
      game('1', '2'),
      game('1', '3'),
    ]);
    expect(sos['1']).toBeCloseTo(0.25);
  });

  it('counts a repeated opponent each time it is faced', () => {
    // Team 1 faces team 2 (0.5) twice and team 3 (0) once -> avg 1/3.
    const sos = computeStrengthOfSchedule(standings, [
      game('1', '2'),
      game('1', '2'),
      game('1', '3'),
    ]);
    expect(sos['1']).toBeCloseTo(1 / 3);
  });

  it('excludes playoff games', () => {
    // The only regular-season opponent for team 1 is team 3 (0).
    const sos = computeStrengthOfSchedule(standings, [
      game('1', '3'),
      game('1', '2', 'WINNERS_BRACKET'),
    ]);
    expect(sos['1']).toBe(0);
  });

  it('skips opponents missing from the standings', () => {
    const sos = computeStrengthOfSchedule(standings, [
      game('1', '2'),
      game('1', '99'),
    ]);
    expect(sos['1']).toBe(0.5);
  });

  it('returns null for a team with no regular-season opponents', () => {
    const sos = computeStrengthOfSchedule(standings, [game('2', '3')]);
    expect(sos['1']).toBeNull();
  });
});
