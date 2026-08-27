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

  test('An in-progress latest season shows the predictor instead of the empty state', ({
    given,
    when,
    then,
  }) => {
    given('the latest season is in progress with games still to play', () => {
      // A played week 1 plus an unplayed (0-0) week 2 regular-season game, no bracket.
      const played = { team_a_score: 100, team_b_score: 90 };
      const unplayed = { team_a_score: 0, team_b_score: 0 };
      const base = {
        team_a_id: 't1',
        team_a_display_name: 'alice',
        team_a_team_name: 'Team alice',
        team_a_team_logo: null,
        team_a_starters: [],
        team_a_bench: [],
        team_a_primary_owner_id: 'p1',
        team_a_secondary_owner_id: null,
        team_b_id: 't2',
        team_b_display_name: 'bob',
        team_b_team_name: 'Team bob',
        team_b_team_logo: null,
        team_b_starters: [],
        team_b_bench: [],
        team_b_primary_owner_id: 'p2',
        team_b_secondary_owner_id: null,
        playoff_tier_type: 'NONE',
        playoff_round: null,
        winner: 't1',
        loser: 't2',
        season: '2024',
      };
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: [
            { ...base, ...played, week: '1' },
            { ...base, ...unplayed, week: '2' },
          ],
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: [
            {
              season: '2024',
              num_playoff_teams: 2,
              num_playoff_teams_assumed: false,
              playoff_week_start: 3,
              regular_season_weeks: 2,
            },
          ],
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
