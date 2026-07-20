import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { PositionalScoring } from '../analytics';

import type { MatchupItem, PlayerStat } from '@/components/api/types';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/analytics/__tests__/positional-scoring.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const NAMES: Record<string, string> = { T1: 'Alice', T2: 'Bob' };

function starter(position: string, points: number): PlayerStat {
  return {
    player_id: Math.floor(Math.random() * 1e6),
    full_name: `${position} player`,
    points_scored: points,
    position,
    fantasy_position: position,
  };
}

function game(
  week: string,
  aId: string,
  bId: string,
  starters: PlayerStat[],
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: NAMES[aId],
    team_a_team_name: `Team ${NAMES[aId]}`,
    team_a_team_logo: null,
    team_a_score: 100,
    team_a_starters: starters,
    team_a_bench: [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: NAMES[bId],
    team_b_team_name: `Team ${NAMES[bId]}`,
    team_b_team_logo: null,
    team_b_score: 90,
    team_b_starters: starters,
    team_b_bench: [],
    team_b_primary_owner_id: `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: aId,
    loser: bId,
    week,
    season: '2024',
  };
}

const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 'T2', [starter('QB', 25), starter('RB', 15)]),
];

async function openChart() {
  await renderRoute(
    <PositionalScoring leagueId="100" platform="SLEEPER" season="2024" />,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('The chart renders a legend of the positions present', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season of matchups with starter stats is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the positional scoring', openChart);
    then(/^I see the position "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
    and(/^I see the position "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
  });

  test('A season without matchup data shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the season has no matchups', () => {
      server.use(leagueQuery({ MATCHUPS: [] }));
    });
    when('I open the positional scoring', openChart);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the matchup data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the positional scoring', openChart);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
