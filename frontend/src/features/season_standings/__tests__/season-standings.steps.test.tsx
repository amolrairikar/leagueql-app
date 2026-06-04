import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import SeasonStandings from '../season-standings';

import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/season_standings/__tests__/season-standings.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const STANDINGS = [
  {
    season: '2024',
    team_id: '1',
    owner_id: 'uA',
    team_name: 'Team Alice',
    team_logo: null,
    owner_username: 'Alice',
    final_rank: 1,
    games_played: 2,
    wins: 2,
    losses: 0,
    ties: 0,
    record: '2-0-0',
    win_pct: 1,
    total_pf: 220,
    total_pa: 180,
    avg_pf: 110,
    avg_pa: 90,
    total_vs_league_wins: 10,
    total_vs_league_losses: 2,
    win_pct_vs_league: 0.83,
    champion: 'Yes',
  },
];

defineFeature(feature, (test) => {
  test('Standings render when data loads', ({ given, when, then }) => {
    given('season standings data is available', () => {
      server.use(
        leagueQuery({ SEASON_STANDINGS: STANDINGS, WEEKLY_STANDINGS: [] }),
      );
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the standings data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
