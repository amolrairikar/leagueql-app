import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import type { MatchupItem, TransactionItem } from '../api-calls';
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

const espnLeague = {
  leagueId: '800',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

// ESPN produces only waiver/free_agent rows (no trades), draft_picks always empty.
const ESPN_TRANSACTIONS: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'e-fa',
    type: 'free_agent',
    week: 2,
    created: 1700000100000,
    roster_ids: ['1'],
    teams: [{ roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' }],
    adds: [
      {
        player_id: '111',
        player_name: 'FA Add',
        position: 'QB',
        roster_id: '1',
      },
    ],
    drops: [
      {
        player_id: '222',
        player_name: 'FA Drop',
        position: 'RB',
        roster_id: '1',
      },
    ],
    draft_picks: [],
    waiver_bid: 0,
  },
  {
    season: '2024',
    transaction_id: 'e-w',
    type: 'waiver',
    week: 1,
    created: 1700000000000,
    roster_ids: ['2'],
    teams: [{ roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' }],
    adds: [
      {
        player_id: '333',
        player_name: 'Waiver Claim',
        position: 'WR',
        roster_id: '2',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: 5,
  },
];

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

// A single trade in week 3: Bob (roster 2) receives "Star Player", Alice (roster 1) receives
// "Role Player" plus a Round 2 pick. Used by the rest-of-season points scenarios below.
const ROS_TRANSACTIONS: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'tr',
    type: 'trade',
    week: 3,
    created: 1700000000000,
    roster_ids: ['1', '2'],
    teams: [
      { roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' },
      { roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' },
    ],
    adds: [
      {
        player_id: '10',
        player_name: 'Star Player',
        position: 'RB',
        roster_id: '2',
      },
      {
        player_id: '11',
        player_name: 'Role Player',
        position: 'WR',
        roster_id: '1',
      },
    ],
    drops: [
      {
        player_id: '10',
        player_name: 'Star Player',
        position: 'RB',
        roster_id: '1',
      },
      {
        player_id: '11',
        player_name: 'Role Player',
        position: 'WR',
        roster_id: '2',
      },
    ],
    draft_picks: [
      { round: 2, season: '2024', from_roster_id: '2', to_roster_id: '1' },
    ],
    waiver_bid: null,
  },
];

/** A minimal matchup box score placing each `{id, pts}` player in week `week`. */
function mkMatchup(
  week: number,
  players: { id: number; pts: number }[],
): MatchupItem {
  return {
    team_a_id: '1',
    team_a_display_name: 'Alice',
    team_a_team_name: 'Team Alice',
    team_a_team_logo: null,
    team_a_score: 0,
    team_a_starters: players.map((p) => ({
      player_id: p.id,
      full_name: `Player ${p.id}`,
      points_scored: p.pts,
      position: 'RB',
    })),
    team_a_bench: [],
    team_a_primary_owner_id: 'o1',
    team_a_secondary_owner_id: null,
    team_b_id: '2',
    team_b_display_name: 'Bob',
    team_b_team_name: 'Team Bob',
    team_b_team_logo: null,
    team_b_score: 0,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: 'o2',
    team_b_secondary_owner_id: null,
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: '',
    loser: '',
    week: String(week),
    season: '2024',
  };
}

// Star Player (id 10) scores 100 in week 2 (before the trade, excluded), then 30 + 40 after it
// → 70.00 for Bob. Role Player (id 11) scores 10 + 15 → 25.00 for Alice. Bob wins by 45.00.
const ROS_MATCHUPS: MatchupItem[] = [
  mkMatchup(2, [{ id: 10, pts: 100 }]),
  mkMatchup(3, [
    { id: 10, pts: 30 },
    { id: 11, pts: 10 },
  ]),
  mkMatchup(4, [
    { id: 10, pts: 40 },
    { id: 11, pts: 15 },
  ]),
];

// Both sides score 20.00 from the trade onward → a tie.
const ROS_MATCHUPS_TIE: MatchupItem[] = [
  mkMatchup(2, [{ id: 10, pts: 100 }]),
  mkMatchup(3, [
    { id: 10, pts: 20 },
    { id: 11, pts: 20 },
  ]),
];

defineFeature(feature, (test) => {
  test('Trades are shown by default with no All option', ({
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
    and(/^I do not see the player "(.*)"$/, (name) => {
      // "Wide Receiver" is a waiver add, hidden while the default Trades filter is active.
      expect(screen.queryByText(name, { exact: false })).toBeNull();
    });
    and('there is no "All" filter option', () => {
      expect(screen.queryByRole('button', { name: 'All' })).toBeNull();
    });
  });

  test('Selecting Free Agents narrows the wire', ({
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
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^I do not see the player "(.*)"$/, (name) => {
      expect(screen.queryByText(name, { exact: false })).toBeNull();
    });
  });

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
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
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
        // Scope to the summary table: the transaction cards also render Bob's avatar (same
        // standings logo), so a page-wide query would match more than one image.
        const table = await screen.findByRole('table');
        const logo = within(table).getByRole('img', { name: 'Team Bob' });
        expect(logo).toHaveAttribute('src', BOB_LOGO);
        // Bob is roster_id 2 → standings index 1, so the avatar uses avatarColor(1)
        // even though he is the first row in the (total-sorted) summary.
        expect(logo.parentElement).toHaveStyle({ background: avatarColor(1) });
      },
    );
  });

  test("A trade shows each side's rest-of-season points and the winner", ({
    given,
    when,
    then,
    and,
  }) => {
    given('a trade with matchup box scores is available', () => {
      server.use(
        leagueQuery({ TRANSACTIONS: ROS_TRANSACTIONS, MATCHUPS: ROS_MATCHUPS }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    and(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    and(/^the trade winner is "(.*)" by "(.*)"$/, async (team, margin) => {
      expect(
        await screen.findByText(`${team} won by ${margin} pts`),
      ).toBeInTheDocument();
    });
  });

  test('Rest-of-season points exclude weeks before the trade', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a trade with matchup box scores is available', () => {
      server.use(
        leagueQuery({ TRANSACTIONS: ROS_TRANSACTIONS, MATCHUPS: ROS_MATCHUPS }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    // Star Player's week-2 (pre-trade) 100 points must be excluded; 170.00 would mean it wasn't.
    and(/^I do not see the points "(.*)"$/, (pts) => {
      expect(screen.queryByText(pts)).toBeNull();
    });
  });

  test('A traded pick shows no points', ({ given, when, then, and }) => {
    given('a trade with matchup box scores is available', () => {
      server.use(
        leagueQuery({ TRANSACTIONS: ROS_TRANSACTIONS, MATCHUPS: ROS_MATCHUPS }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the traded pick "(.*)"$/, async (label) => {
      expect(
        (await screen.findAllByText(label, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^a received item shows no points "(.*)"$/, async (dash) => {
      expect((await screen.findAllByText(dash)).length).toBeGreaterThan(0);
    });
  });

  test('Evenly scored trade sides show a tie', ({ given, when, then, and }) => {
    given('a trade with evenly scored matchup box scores is available', () => {
      server.use(
        leagueQuery({
          TRANSACTIONS: ROS_TRANSACTIONS,
          MATCHUPS: ROS_MATCHUPS_TIE,
        }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the trade tie message "(.*)"$/, async (msg) => {
      expect(
        (await screen.findAllByText(msg, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and('there is no trade winner', () => {
      expect(screen.queryByText(/won by/)).toBeNull();
    });
  });

  test('A trade renders without points when box scores are unavailable', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a trade with no matchup box scores is available', () => {
      // No MATCHUPS key → the matchups query 404s, which degrades silently to no points.
      server.use(leagueQuery({ TRANSACTIONS: ROS_TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and('there is no trade winner', () => {
      expect(screen.queryByText(/won by/)).toBeNull();
      expect(screen.queryByText(/Even/)).toBeNull();
    });
    and(/^I do not see the message "(.*)"$/, (msg) => {
      expect(screen.queryByText(msg)).toBeNull();
    });
  });

  test('ESPN defaults to Free Agents and offers no Trades filter', ({
    given,
    when,
    then,
    and,
  }) => {
    given('ESPN transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS: ESPN_TRANSACTIONS }));
    });
    when('I open the transactions page for an ESPN league', async () => {
      await renderRoute(<Transactions />, {
        route: '/transactions',
        league: espnLeague,
      });
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      // The Free-Agent default is active, so the free-agent add is shown.
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    and(/^there is no "(.*)" filter option$/, (label) => {
      expect(screen.queryByRole('button', { name: label })).toBeNull();
    });
    and('there is no "All" filter option', () => {
      expect(screen.queryByRole('button', { name: 'All' })).toBeNull();
    });
  });

  test('An ESPN waiver shows the claimed player when the Waivers filter is selected', ({
    given,
    when,
    then,
    and,
  }) => {
    given('ESPN transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS: ESPN_TRANSACTIONS }));
    });
    when('I open the transactions page for an ESPN league', async () => {
      await renderRoute(<Transactions />, {
        route: '/transactions',
        league: espnLeague,
      });
    });
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
  });

  test('The ESPN summary table omits the Trades column', ({
    given,
    when,
    then,
    and,
  }) => {
    given('ESPN transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS: ESPN_TRANSACTIONS }));
    });
    when('I open the transactions page for an ESPN league', async () => {
      await renderRoute(<Transactions />, {
        route: '/transactions',
        league: espnLeague,
      });
    });
    then(/^the summary table has no "(.*)" column$/, async (label) => {
      // Wait for the summary table to render before asserting the column is absent.
      await screen.findByRole('columnheader', { name: 'Free Agents' });
      expect(screen.queryByRole('columnheader', { name: label })).toBeNull();
    });
    and(/^the summary table has a "(.*)" column$/, (label) => {
      expect(
        screen.getByRole('columnheader', { name: label }),
      ).toBeInTheDocument();
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
