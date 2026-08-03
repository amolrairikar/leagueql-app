import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import PlayoffBracket from '../playoff-bracket';

import {
  LEAGUE,
  MATCHUPS,
  PLAYOFF_BRACKET,
  PLAYOFF_BRACKET_SIX_TEAM,
  WEEKLY_STANDINGS,
} from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/playoff_bracket/__tests__/playoff-bracket.feature',
);

defineFeature(feature, (test) => {
  test('The bracket renders when data loads', ({ given, when, then }) => {
    given('playoff bracket data is available', () => {
      server.use(leagueQuery({ PLAYOFF_BRACKET, MATCHUPS, WEEKLY_STANDINGS }));
    });
    when('I open the playoff bracket page', async () => {
      await renderRoute(<PlayoffBracket />, {
        route: '/playoff_bracket',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the playoff bracket data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the playoff bracket page', async () => {
      await renderRoute(<PlayoffBracket />, {
        route: '/playoff_bracket',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('A bracket with byes renders the wildcard round matchups', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a six-team bracket with byes is available', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: PLAYOFF_BRACKET_SIX_TEAM,
          MATCHUPS: [],
          WEEKLY_STANDINGS: [],
        }),
      );
    });
    when('I open the playoff bracket page', async () => {
      await renderRoute(<PlayoffBracket />, {
        route: '/playoff_bracket',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A season with no bracket shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the selected season has no playoff bracket', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: [],
          WEEKLY_STANDINGS: [],
        }),
      );
    });
    when('I open the playoff bracket page', async () => {
      await renderRoute(<PlayoffBracket />, {
        route: '/playoff_bracket',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
