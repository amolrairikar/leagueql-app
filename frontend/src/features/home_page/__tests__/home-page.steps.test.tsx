import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import HomePage from '../home-page';

import {
  leagueMetadata,
  leagueQuery,
  leagueQueryError,
  server,
} from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/home_page/__tests__/home-page.feature',
);

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
    total_pf: 220,
    avg_pf: 110,
    champion: 'Yes',
  },
];

const MATCHUPS = [
  {
    season: '2024',
    week: '1',
    team_a_id: '1',
    team_a_display_name: 'Alice',
    team_a_team_name: 'Team Alice',
    team_a_team_logo: null,
    team_a_primary_owner_id: 'uA',
    team_a_secondary_owner_id: null,
    team_a_score: 110,
    team_b_id: '2',
    team_b_display_name: 'Bob',
    team_b_team_name: 'Team Bob',
    team_b_team_logo: null,
    team_b_primary_owner_id: 'uB',
    team_b_secondary_owner_id: null,
    team_b_score: 95,
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: '1',
    loser: '2',
  },
];

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

defineFeature(feature, (test) => {
  test('The dashboard renders stats, champions and standings when data loads', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a connected league with home dashboard data', () => {
      server.use(
        leagueMetadata({ league_name: 'My League', seasons: ['2024'] }),
        leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS: MATCHUPS }),
      );
    });
    when('I open the home dashboard', async () => {
      await renderRoute(<HomePage />, { route: '/home', league });
    });
    then(/^I see the league name "(.*)"$/, async (name) => {
      expect(await screen.findByText(name)).toBeInTheDocument();
    });
    and(/^I see the headline stat "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I see the champion manager "(.*)"$/, async (owner) => {
      expect((await screen.findAllByText(owner)).length).toBeGreaterThan(0);
    });
  });

  test('A failed data load shows a single inline error', ({
    given,
    when,
    then,
  }) => {
    given('a connected league whose data fails to load', () => {
      server.use(
        leagueMetadata({ league_name: 'My League', seasons: ['2024'] }),
        leagueQueryError(500),
      );
    });
    when('I open the home dashboard', async () => {
      await renderRoute(<HomePage />, { route: '/home', league });
    });
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });

  test('A league with no games shows an empty standings state', ({
    given,
    when,
    then,
  }) => {
    given('a connected league with no games yet', () => {
      server.use(
        leagueMetadata({ league_name: 'My League', seasons: ['2024'] }),
        leagueQuery({ SEASON_STANDINGS: [], MATCHUPS: [] }),
      );
    });
    when('I open the home dashboard', async () => {
      await renderRoute(<HomePage />, { route: '/home', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('The dashboard renders without crashing when seasons cookie has expired', ({
    given,
    when,
    then,
  }) => {
    given('a connected league with no seasons', () => {
      server.use(
        leagueMetadata({ league_name: 'My League', seasons: [] }),
        leagueQuery({ SEASON_STANDINGS: [], MATCHUPS: [] }),
      );
    });
    when('I open the home dashboard', async () => {
      await renderRoute(<HomePage />, {
        route: '/home',
        league: { ...league, seasons: [] },
      });
    });
    then(/^I see the headline stat "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
  });
});
