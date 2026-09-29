import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
        player_id: 9999,
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

// The regular-season week 1, plus a 2-week playoff game whose inflated starter must
// only surface once the page is switched to postseason records.
const MATCHUPS_WITH_POSTSEASON: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]),
  {
    ...(MATCHUPS[0] as MatchupItem),
    week: '15',
    team_a_score: 260,
    team_b_score: 240,
    team_a_starters: [
      {
        player_id: 8888,
        full_name: 'Playoff Hero',
        points_scored: 70,
        position: 'QB',
        fantasy_position: 'QB',
      },
    ],
    team_b_starters: [],
    playoff_tier_type: 'WINNERS_BRACKET',
    playoff_round: 'Finals',
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

  test('Postseason performances are excluded by default', ({
    given,
    when,
    then,
  }) => {
    given('player box-score data includes a postseason week', () => {
      server.use(leagueQuery({ MATCHUPS: MATCHUPS_WITH_POSTSEASON }));
    });
    when('I open the player records page', async () => {
      await renderRoute(<PlayerRecords />, {
        route: '/player_records',
        league: LEAGUE,
      });
    });
    then(/^I do not see the player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText('Pat Quarterback')).length,
      ).toBeGreaterThan(0);
      expect(screen.queryByText(name)).toBeNull();
    });
  });

  test('Toggling to Postseason shows only postseason performances', ({
    given,
    when,
    and,
    then,
  }) => {
    given('player box-score data includes a postseason week', () => {
      server.use(leagueQuery({ MATCHUPS: MATCHUPS_WITH_POSTSEASON }));
    });
    when('I open the player records page', async () => {
      await renderRoute(<PlayerRecords />, {
        route: '/player_records',
        league: LEAGUE,
      });
    });
    and('I switch to postseason records', async () => {
      await userEvent.click(
        await screen.findByRole('switch', { name: /postseason/i }),
      );
    });
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and(/^I do not see the player "(.*)"$/, (name) => {
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
