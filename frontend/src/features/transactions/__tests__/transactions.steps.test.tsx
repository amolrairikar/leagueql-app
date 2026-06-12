import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import type { TransactionItem } from '../api-calls';
import Transactions from '../transactions';

import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/transactions/__tests__/transactions.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const TRANSACTIONS: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 't1',
    type: 'trade',
    week: 1,
    created: 1700000000000,
    roster_ids: ['1', '2'],
    teams: [
      { roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' },
      { roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' },
    ],
    adds: [
      {
        player_id: 'p1',
        player_name: 'Pat Quarterback',
        position: 'QB',
        roster_id: '2',
      },
      {
        player_id: 'p2',
        player_name: 'Run Back',
        position: 'RB',
        roster_id: '1',
      },
    ],
    drops: [
      {
        player_id: 'p1',
        player_name: 'Pat Quarterback',
        position: 'QB',
        roster_id: '1',
      },
    ],
    draft_picks: [],
    waiver_bid: null,
  },
];

defineFeature(feature, (test) => {
  test('Transactions render when data loads', ({ given, when, then, and }) => {
    given('transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(
        (await screen.findAllByText(text, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect(
        (await screen.findAllByText(text, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
  });

  test('A season with no transactions shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the league has no transactions', () => {
      // No TRANSACTIONS key → the query 404s, which getTransactions maps to empty.
      server.use(leagueQuery({}));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the transactions data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
