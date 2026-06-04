import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import ManagerComparison from '../manager-comparison';

import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/manager_comparison/__tests__/manager-comparison.feature',
);

defineFeature(feature, (test) => {
  test('A head-to-head comparison renders when data loads', ({
    given,
    when,
    then,
  }) => {
    given('comparison data for two managers is available', () => {
      server.use(leagueQuery({ MATCHUPS, PLATFORM_MIGRATION: [] }));
    });
    when('I open the manager comparison page', async () => {
      await renderRoute(<ManagerComparison />, {
        route: '/manager_comparison',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('Too few managers shows a zero-state', ({ given, when, then }) => {
    given('there is no comparison data', () => {
      server.use(leagueQuery({ MATCHUPS: [], PLATFORM_MIGRATION: [] }));
    });
    when('I open the manager comparison page', async () => {
      await renderRoute(<ManagerComparison />, {
        route: '/manager_comparison',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
