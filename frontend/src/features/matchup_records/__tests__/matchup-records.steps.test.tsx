import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import MatchupRecords from '../matchup-records';

import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/matchup_records/__tests__/matchup-records.feature',
);

defineFeature(feature, (test) => {
  test('Matchup records render when data loads', ({ given, when, then }) => {
    given('matchup records data is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the matchup records page', async () => {
      await renderRoute(<MatchupRecords />, {
        route: '/matchup_records',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the matchup records data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the matchup records page', async () => {
      await renderRoute(<MatchupRecords />, {
        route: '/matchup_records',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
