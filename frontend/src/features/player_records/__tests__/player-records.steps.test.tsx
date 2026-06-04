import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import PlayerRecords from '../player-records';

import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/player_records/__tests__/player-records.feature',
);

defineFeature(feature, (test) => {
  test('Player records render when data loads', ({ given, when, then }) => {
    given('player box-score data is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the player records page', async () => {
      await renderRoute(<PlayerRecords />, {
        route: '/player_records',
        league: LEAGUE,
      });
    });
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the player data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the player records page', async () => {
      await renderRoute(<PlayerRecords />, {
        route: '/player_records',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
