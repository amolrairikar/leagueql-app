import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import Matchups from '../matchups';

import { LEAGUE, MATCHUPS, WEEKLY_STANDINGS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/matchups/__tests__/matchups.feature');

defineFeature(feature, (test) => {
  test('Matchups render when data loads', ({ given, when, then }) => {
    given('matchup data is available', () => {
      server.use(leagueQuery({ MATCHUPS, WEEKLY_STANDINGS }));
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the matchup data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
