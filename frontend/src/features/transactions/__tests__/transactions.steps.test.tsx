import { screen, within } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import type { TransactionItem } from '../api-calls';
import Transactions from '../transactions';

import { avatarColor } from '@/lib/color-constants';
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
    // Bob receives Pat Quarterback; Alice receives Run Back. The mirrored drops
    // (Alice drops Pat, Bob drops Run) must NOT be rendered for a trade.
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
      {
        player_id: 'p2',
        player_name: 'Run Back',
        position: 'RB',
        roster_id: '2',
      },
    ],
    draft_picks: [
      {
        round: 2,
        season: '2024',
        from_roster_id: '1',
        to_roster_id: '2',
      },
    ],
    waiver_bid: null,
  },
  {
    season: '2024',
    transaction_id: 't2',
    type: 'waiver',
    week: 2,
    created: 1700000100000,
    roster_ids: ['1'],
    teams: [{ roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' }],
    adds: [
      {
        player_id: 'p3',
        player_name: 'Wide Receiver',
        position: 'WR',
        roster_id: '1',
      },
    ],
    drops: [
      {
        player_id: 'p4',
        player_name: 'Bench Guy',
        position: 'TE',
        roster_id: '1',
      },
    ],
    draft_picks: [],
    waiver_bid: 7,
  },
  // Two free-agent pickups for Bob. Combined with the trade above, Bob's totals
  // (FA 2, trade 1, total 3) outrank Alice's (waiver 1, trade 1, total 2), so the
  // summary table must list Bob first despite "Bob" sorting after "Alice" by name.
  {
    season: '2024',
    transaction_id: 't3',
    type: 'free_agent',
    week: 3,
    created: 1700000200000,
    roster_ids: ['2'],
    teams: [{ roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' }],
    adds: [
      {
        player_id: 'p5',
        player_name: 'Free Agent One',
        position: 'RB',
        roster_id: '2',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  },
  {
    season: '2024',
    transaction_id: 't4',
    type: 'free_agent',
    week: 4,
    created: 1700000300000,
    roster_ids: ['2'],
    teams: [{ roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' }],
    adds: [
      {
        player_id: 'p6',
        player_name: 'Free Agent Two',
        position: 'WR',
        roster_id: '2',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  },
];

// Standings for the same season (team_id is the roster_id for Sleeper), ordered Alice then
// Bob. The summary lists Bob first (higher total), so reusing the *standings* index proves
// Bob takes the second avatar color (avatarColor(1)) — not the first, which the summary's own
// row order would give — and that the avatar shows the standings logo.
const BOB_LOGO = 'https://logos.test/bob.png';
const STANDINGS = [
  {
    team_id: '1',
    team_name: 'Team Alice',
    team_logo: 'https://logos.test/alice.png',
  },
  { team_id: '2', team_name: 'Team Bob', team_logo: BOB_LOGO },
];

defineFeature(feature, (test) => {
  test('A trade shows only what each team received', ({
    given,
    when,
    then,
    and,
  }) => {
    given('transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^I see the traded pick "(.*)"$/, async (label) => {
      expect(
        (await screen.findAllByText(label, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^"(.*)" is shown only once$/, async (name) => {
      // The trade's mirrored drop is hidden, so the player appears exactly once.
      expect((await screen.findAllByText(name, { exact: false })).length).toBe(
        1,
      );
    });
  });

  test('A waiver shows both the add and the drop', ({
    given,
    when,
    then,
    and,
  }) => {
    given('transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
  });

  test('The summary table breaks down activity per owner', ({
    given,
    when,
    then,
    and,
  }) => {
    given('transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    const checkRow = async (
      name: string,
      waivers: string,
      freeAgents: string,
      trades: string,
      total: string,
    ) => {
      // The owner cell now holds the avatar initials, username, and team name,
      // so match the username as a substring of the cell's accessible name.
      const ownerCell = await screen.findByRole('cell', {
        name: new RegExp(name),
      });
      const cells = within(ownerCell.closest('tr')!).getAllByRole('cell');
      expect(cells[1].textContent).toBe(waivers);
      expect(cells[2].textContent).toBe(freeAgents);
      expect(cells[3].textContent).toBe(trades);
      expect(cells[4].textContent).toBe(total);
    };
    then(
      /^the summary row for "(.*)" shows waivers "(.*)", free agents "(.*)", trades "(.*)", total "(.*)"$/,
      checkRow,
    );
    and(
      /^the summary row for "(.*)" shows waivers "(.*)", free agents "(.*)", trades "(.*)", total "(.*)"$/,
      checkRow,
    );
    and(
      /^owner "(.*)" is listed above owner "(.*)" in the summary table$/,
      async (first, second) => {
        const firstRow = (
          await screen.findByRole('cell', { name: new RegExp(first) })
        ).closest('tr')!;
        const secondRow = (
          await screen.findByRole('cell', { name: new RegExp(second) })
        ).closest('tr')!;
        const rows = screen.getAllByRole('row');
        expect(rows.indexOf(firstRow)).toBeLessThan(rows.indexOf(secondRow));
      },
    );
  });

  test("The summary reuses each owner's Season Standings avatar and color", ({
    given,
    when,
    then,
  }) => {
    given('transactions and standings data are available', () => {
      server.use(leagueQuery({ TRANSACTIONS, SEASON_STANDINGS: STANDINGS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(
      'owner "Bob" shows the standings team logo and standings color',
      async () => {
        const logo = await screen.findByRole('img', { name: 'Team Bob' });
        expect(logo).toHaveAttribute('src', BOB_LOGO);
        // Bob is roster_id 2 → standings index 1, so the avatar uses avatarColor(1)
        // even though he is the first row in the (total-sorted) summary.
        expect(logo.parentElement).toHaveStyle({ background: avatarColor(1) });
      },
    );
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
    then(/^I see the message "(.*)"$/, async (text) => {
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
    then(/^I see the message "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
