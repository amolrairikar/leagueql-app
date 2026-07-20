import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { PowerRankings } from '../analytics';

import type { MatchupItem } from '@/components/api/types';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/analytics/__tests__/power-rankings.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const NAMES: Record<string, string> = { T1: 'Alice', T2: 'Bob' };

function game(
  week: string,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
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
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week,
    season: '2024',
  };
}

const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 100, 'T2', 90),
  game('2', 'T1', 110, 'T2', 80),
  game('3', 'T1', 95, 'T2', 105),
];

async function openChart() {
  await renderRoute(
    <PowerRankings leagueId="100" platform="SLEEPER" season="2024" />,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('The chart renders a line per manager for a season', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season of regular-season matchups is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the power rankings', openChart);
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A season without enough data shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the season has no regular-season matchups', () => {
      server.use(leagueQuery({ MATCHUPS: [] }));
    });
    when('I open the power rankings', openChart);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the matchup data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the power rankings', openChart);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
