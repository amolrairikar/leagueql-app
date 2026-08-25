import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import ManagerComparison from '../manager-comparison';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

// Alice beat Bob in week 1; week 2 is an unplayed 0-0 placeholder between the same
// two managers. Counted, it would add a phantom tie (records → 1-0-1) and a second
// game-log row; it must be excluded from both.
const MATCHUPS_WITH_UNPLAYED: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]),
  {
    ...(MATCHUPS[0] as MatchupItem),
    week: '2',
    team_a_score: 0,
    team_b_score: 0,
    winner: 'TIE',
    loser: 'TIE',
  },
];

const feature = loadFeature(
  'src/features/manager_comparison/__tests__/manager-comparison.feature',
);

defineFeature(feature, (test) => {
  test('A head-to-head comparison renders when data loads', ({
    given,
    when,
    then,
  }) => {
    given('comparison data for two managers is available', () => {
      server.use(leagueQuery({ MATCHUPS, PLATFORM_MIGRATION: [] }));
    });
    when('I open the manager comparison page', async () => {
      await renderRoute(<ManagerComparison />, {
        route: '/manager_comparison',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('An unplayed 0-0 week is excluded from records and the game log', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'comparison data includes an unplayed 0-0 week between the two managers',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: MATCHUPS_WITH_UNPLAYED,
            PLATFORM_MIGRATION: [],
          }),
        );
      },
    );
    when('I open the manager comparison page', async () => {
      await renderRoute(<ManagerComparison />, {
        route: '/manager_comparison',
        league: LEAGUE,
      });
    });
    then(
      /^the record shows "(.*)" and no phantom tie "(.*)"$/,
      async (record, phantom) => {
        // Alice's record stays 1-0-0; a counted 0-0 tie would make it 1-0-1.
        expect(await screen.findByText(new RegExp(record))).toBeInTheDocument();
        expect(screen.queryByText(new RegExp(phantom))).toBeNull();
      },
    );
    and(/^the game log has no "(.*)" score$/, (score) => {
      // The excluded 0-0 week would otherwise add a game-log row scoring 0.0.
      expect(screen.queryByText(score)).toBeNull();
    });
  });

  test('Too few managers shows a zero-state', ({ given, when, then }) => {
    given('there is no comparison data', () => {
      server.use(leagueQuery({ MATCHUPS: [], PLATFORM_MIGRATION: [] }));
    });
    when('I open the manager comparison page', async () => {
      await renderRoute(<ManagerComparison />, {
        route: '/manager_comparison',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
