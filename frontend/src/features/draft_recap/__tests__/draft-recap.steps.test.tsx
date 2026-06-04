import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import DraftRecap from '../draft-recap';

import { DRAFT, LEAGUE } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/draft_recap/__tests__/draft-recap.feature',
);

defineFeature(feature, (test) => {
  test('The draft board renders when data loads', ({ given, when, then }) => {
    given('draft data is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft recap page', async () => {
      await renderRoute(<DraftRecap />, {
        route: '/draft_recap',
        league: LEAGUE,
      });
    });
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the draft data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the draft recap page', async () => {
      await renderRoute(<DraftRecap />, {
        route: '/draft_recap',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
