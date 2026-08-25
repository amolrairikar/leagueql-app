import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import PlayerRecords from '../player-records';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

// The played week 1, plus an unplayed 0-0 placeholder week 2 whose starters include a
// uniquely named player. Because the matchup is 0-0, none of its players may surface.
const MATCHUPS_WITH_UNPLAYED: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]),
  {
    ...(MATCHUPS[0] as MatchupItem),
    week: '2',
    team_a_score: 0,
    team_b_score: 0,
    team_a_starters: [
      {
        player_id: 'phantom',
        full_name: 'Phantom Player',
        points_scored: 0,
        position: 'QB',
        fantasy_position: 'QB',
      },
    ],
    winner: 'TIE',
    loser: 'TIE',
  },
];

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

  test("An unplayed 0-0 week's players never surface on a score board", ({
    given,
    when,
    then,
  }) => {
    given('player box-score data includes an unplayed 0-0 week', () => {
      server.use(leagueQuery({ MATCHUPS: MATCHUPS_WITH_UNPLAYED }));
    });
    when('I open the player records page', async () => {
      await renderRoute(<PlayerRecords />, {
        route: '/player_records',
        league: LEAGUE,
      });
    });
    then(/^I do not see the player "(.*)"$/, async (name) => {
      // Wait for the page's real content before asserting the phantom is absent.
      expect(
        (await screen.findAllByText('Pat Quarterback')).length,
      ).toBeGreaterThan(0);
      expect(screen.queryByText(name)).toBeNull();
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
