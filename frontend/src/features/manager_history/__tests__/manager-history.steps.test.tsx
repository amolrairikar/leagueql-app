import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import ManagerHistory from '../manager-history';

import { LEAGUE, MATCHUPS, STANDINGS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/manager_history/__tests__/manager-history.feature',
);

defineFeature(feature, (test) => {
  test('Manager history renders when data loads', ({ given, when, then }) => {
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the manager history data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
