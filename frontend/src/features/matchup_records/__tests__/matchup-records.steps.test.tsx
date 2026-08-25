import { screen, within } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import MatchupRecords from '../matchup-records';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

// The played week, plus an unplayed 0-0 placeholder between Cara and Dan. If it
// were counted, Cara's 0.00 would top the Lowest Team Score board; it must not.
const MATCHUPS_WITH_UNPLAYED: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]),
  {
    ...(MATCHUPS[0] as MatchupItem),
    week: '2',
    team_a_id: '3',
    team_a_display_name: 'Cara',
    team_a_team_name: 'Team Cara',
    team_a_score: 0,
    team_b_id: '4',
    team_b_display_name: 'Dan',
    team_b_team_name: 'Team Dan',
    team_b_score: 0,
    winner: '3',
    loser: '4',
  },
];

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

  test('Both teams in one matchup rank in the Lowest Team Score card', ({
    given,
    when,
    then,
  }) => {
    given('matchup records data is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the matchup records page', async () => {
      await renderRoute(<MatchupRecords />, {
        route: '/matchup_records',
        league: LEAGUE,
      });
    });
    then(
      /^the "(.*)" card lists both "(.*)" and "(.*)"$/,
      async (cardLabel, teamA, teamB) => {
        const label = await screen.findByText(cardLabel);
        const card = label.closest<HTMLElement>('div.bg-card');
        expect(card).not.toBeNull();
        expect(within(card!).getByText(teamA)).toBeInTheDocument();
        expect(within(card!).getByText(teamB)).toBeInTheDocument();
      },
    );
  });

  test('An unplayed 0-0 matchup never surfaces on a record board', ({
    given,
    when,
    then,
  }) => {
    given('matchup records data includes an unplayed 0-0 week', () => {
      server.use(leagueQuery({ MATCHUPS: MATCHUPS_WITH_UNPLAYED }));
    });
    when('I open the matchup records page', async () => {
      await renderRoute(<MatchupRecords />, {
        route: '/matchup_records',
        league: LEAGUE,
      });
    });
    then(/^the "(.*)" card does not list "(.*)"$/, async (cardLabel, name) => {
      const label = await screen.findByText(cardLabel);
      const card = label.closest<HTMLElement>('div.bg-card');
      expect(card).not.toBeNull();
      expect(within(card!).queryByText(name)).toBeNull();
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
