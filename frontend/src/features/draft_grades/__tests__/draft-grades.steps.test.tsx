import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import DraftGrades from '../draft-grades';

import { DRAFT, LEAGUE } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/draft_grades/__tests__/draft-grades.feature',
);

defineFeature(feature, (test) => {
  test('Draft grades render when data loads', ({ given, when, then }) => {
    given('draft grade data is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A pick with no scoring data renders without crashing', ({
    given,
    when,
    then,
  }) => {
    given('draft grade data is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the draft grade data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
