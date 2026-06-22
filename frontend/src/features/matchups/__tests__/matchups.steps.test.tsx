import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import Matchups from '../matchups';

import { LEAGUE, MATCHUPS, WEEKLY_STANDINGS } from '@/test/fixtures';
import {
  leagueMetadata,
  leagueQuery,
  leagueQueryError,
  server,
} from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/matchups/__tests__/matchups.feature');

const RECAP = {
  season: '2024',
  week: '1',
  headline: 'Week 1 Recap: Alice Cruises',
  body: 'Alice rolled to a comfortable win to open the season.',
  model: 'amazon.nova-lite-v1:0',
  generated_at: '2026-06-19T12:00:00+00:00',
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

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

  // Regression (FE-033): the recap section is gated outside the matchups Suspense
  // boundary and needs a concrete week to fetch. The page must feed it the resolved
  // active week (latest when none picked), so the recap loads on first render — not
  // only after the user clicks a week button.
  test('The AI recap loads for the latest week on first render', ({
    given,
    when,
    then,
  }) => {
    given('matchup and recap data are available', () => {
      server.use(
        leagueMetadata({
          seasons: ['2024'],
          subscription_end_time: isoIn(30),
        }),
        leagueQuery({ MATCHUPS, WEEKLY_STANDINGS, RECAP: [RECAP] }),
      );
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see the recap headline "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
