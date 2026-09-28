import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';

import type { MatchupItem, TransactionItem } from '../api-calls';
import Transactions from '../transactions';

import { avatarColor } from '@/lib/color-constants';
import { API, leagueQuery, leagueQueryError, server } from '@/test/msw/server';
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

// A week-3 free-agent move for Alice (roster 1): add "Pickup Hero" (id 20), drop "Cut Loose"
// (id 21). Used by the waiver/free-agent rest-of-season scenarios.
const ROS_FA_ADD_DROP: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'fa-ad',
    type: 'free_agent',
    week: 3,
    created: 1700000000000,
    roster_ids: ['1'],
    teams: [{ roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' }],
    adds: [
      {
        player_id: '20',
        player_name: 'Pickup Hero',
        position: 'WR',
        roster_id: '1',
      },
    ],
    drops: [
      {
        player_id: '21',
        player_name: 'Cut Loose',
        position: 'RB',
        roster_id: '1',
      },
    ],
    draft_picks: [],
    waiver_bid: null,
  },
];

// Pickup Hero (id 20) scores 100 in week 2 (before the move, excluded), then 30 + 30 = 60.00.
// Cut Loose (id 21) scores 5 + 10 = 15.00. Net pickup value = 60.00 − 15.00 = +45.00.
const ROS_FA_ADD_DROP_MATCHUPS: MatchupItem[] = [
  mkMatchup(2, [{ id: 20, pts: 100 }]),
  mkMatchup(3, [
    { id: 20, pts: 30 },
    { id: 21, pts: 5 },
  ]),
  mkMatchup(4, [
    { id: 20, pts: 30 },
    { id: 21, pts: 10 },
  ]),
];

// A week-3 pure free-agent add for Alice: "Lone Add" (id 22), no drop → 12 + 8 = 20.00, no net.
const ROS_FA_PURE_ADD: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'fa-add',
    type: 'free_agent',
    week: 3,
    created: 1700000000000,
    roster_ids: ['1'],
    teams: [{ roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' }],
    adds: [
      {
        player_id: '22',
        player_name: 'Lone Add',
        position: 'TE',
        roster_id: '1',
      },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  },
];

const ROS_FA_PURE_ADD_MATCHUPS: MatchupItem[] = [
  mkMatchup(3, [{ id: 22, pts: 12 }]),
  mkMatchup(4, [{ id: 22, pts: 8 }]),
];

// A week-3 pure free-agent drop for Alice: "Lone Drop" (id 23), no add → 3 + 4 = 7.00, no net.
const ROS_FA_PURE_DROP: TransactionItem[] = [
  {
    season: '2024',
    transaction_id: 'fa-drop',
    type: 'free_agent',
    week: 3,
    created: 1700000000000,
    roster_ids: ['1'],
    teams: [{ roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' }],
    adds: [],
    drops: [
      {
        player_id: '23',
        player_name: 'Lone Drop',
        position: 'RB',
        roster_id: '1',
      },
    ],
    draft_picks: [],
    waiver_bid: null,
  },
];

const ROS_FA_PURE_DROP_MATCHUPS: MatchupItem[] = [
  mkMatchup(3, [{ id: 23, pts: 3 }]),
  mkMatchup(4, [{ id: 23, pts: 4 }]),
];

/** A week-1 move among Alice (roster 1) and Bob (roster 2) for the top-transactions scenarios. */
function mkMove(
  id: string,
  type: TransactionItem['type'],
  created: number,
  adds: { id: string; name: string; roster: string }[],
  drops: { id: string; name: string; roster: string }[] = [],
  waiverBid: number | null = null,
): TransactionItem {
  const player = (p: { id: string; name: string; roster: string }) => ({
    player_id: p.id,
    player_name: p.name,
    position: null,
    roster_id: p.roster,
  });
  const rosters = [...new Set([...adds, ...drops].map((p) => p.roster))].sort();
  const TEAMS: Record<string, TransactionItem['teams'][number]> = {
    '1': { roster_id: '1', team_name: 'Team Alice', display_name: 'Alice' },
    '2': { roster_id: '2', team_name: 'Team Bob', display_name: 'Bob' },
  };
  return {
    season: '2024',
    transaction_id: id,
    type,
    week: 1,
    created,
    roster_ids: rosters,
    teams: rosters.map((r) => TEAMS[r]),
    adds: adds.map(player),
    drops: drops.map(player),
    draft_picks: [],
    waiver_bid: waiverBid,
  };
}

const A = '1';
const B = '2';

// Impacts (ROS points from week 1): Big Pickup waiver +90 (100 − 10), Solid Add FA +60, the
// Star/Role trade won by Bob +45 (70 − 25), Late Add waiver +30, Minor Add FA +15 (20 − 5), Sixth
// Add FA +10 (6th, cut), Bust FA −45 (net-negative, excluded), Even Swap trade 8 v 8 (excluded).
const TOP_MIXED: TransactionItem[] = [
  mkMove(
    'w-big',
    'waiver',
    1,
    [{ id: '30', name: 'Big Pickup', roster: A }],
    [{ id: '31', name: 'Scrub', roster: A }],
    12,
  ),
  mkMove(
    'tr-star',
    'trade',
    2,
    [
      { id: '10', name: 'Star Player', roster: B },
      { id: '11', name: 'Role Player', roster: A },
    ],
    [
      { id: '10', name: 'Star Player', roster: A },
      { id: '11', name: 'Role Player', roster: B },
    ],
  ),
  mkMove('fa-solid', 'free_agent', 3, [
    { id: '32', name: 'Solid Add', roster: B },
  ]),
  mkMove(
    'fa-minor',
    'free_agent',
    4,
    [{ id: '33', name: 'Minor Add', roster: A }],
    [{ id: '34', name: 'Minor Drop', roster: A }],
  ),
  mkMove('w-late', 'waiver', 5, [{ id: '35', name: 'Late Add', roster: B }]),
  mkMove('fa-sixth', 'free_agent', 6, [
    { id: '36', name: 'Sixth Add', roster: B },
  ]),
  mkMove(
    'fa-bust',
    'free_agent',
    7,
    [{ id: '37', name: 'Bust', roster: A }],
    [{ id: '38', name: 'Keeper', roster: A }],
  ),
  mkMove(
    'tr-even',
    'trade',
    8,
    [
      { id: '39', name: 'Even Swap A', roster: A },
      { id: '40', name: 'Even Swap B', roster: B },
    ],
    [
      { id: '39', name: 'Even Swap A', roster: B },
      { id: '40', name: 'Even Swap B', roster: A },
    ],
  ),
];

const TOP_MIXED_MATCHUPS: MatchupItem[] = [
  mkMatchup(1, [
    { id: 30, pts: 100 },
    { id: 31, pts: 10 },
    { id: 10, pts: 70 },
    { id: 11, pts: 25 },
    { id: 32, pts: 60 },
    { id: 33, pts: 20 },
    { id: 34, pts: 5 },
    { id: 35, pts: 30 },
    { id: 36, pts: 10 },
    { id: 37, pts: 5 },
    { id: 38, pts: 50 },
    { id: 39, pts: 8 },
    { id: 40, pts: 8 },
  ]),
];

// Two +20 pickups; the later-created one is listed first in the data, so the tie-break (earlier
// transaction first) is what puts "Early Add" on top.
const TOP_TIE: TransactionItem[] = [
  mkMove('fa-later', 'free_agent', 20, [
    { id: '41', name: 'Later Add', roster: B },
  ]),
  mkMove('fa-early', 'free_agent', 10, [
    { id: '42', name: 'Early Add', roster: A },
  ]),
];

const TOP_TIE_MATCHUPS: MatchupItem[] = [
  mkMatchup(1, [
    { id: 41, pts: 20 },
    { id: 42, pts: 20 },
  ]),
];

const atWeek = (week: number, txn: TransactionItem): TransactionItem => ({
  ...txn,
  week,
});

// Alice picks up "Short Stint" (id 50) for "Old Guy" (id 51) in week 3, then cuts Short Stint in
// week 5. Short Stint: 10 + 20 while rostered (weeks 3–4), then 100 + 100 elsewhere → 30.00, not
// 230.00. Old Guy keeps his full rest of season, including week 6 after the cut: 5 + 10 = 15.00.
// Net = 30.00 − 15.00 = +15.00.
const REDROP: TransactionItem[] = [
  atWeek(
    3,
    mkMove(
      'fa-stint',
      'free_agent',
      100,
      [{ id: '50', name: 'Short Stint', roster: A }],
      [{ id: '51', name: 'Old Guy', roster: A }],
    ),
  ),
  atWeek(
    5,
    mkMove(
      'fa-cut',
      'free_agent',
      200,
      [],
      [{ id: '50', name: 'Short Stint', roster: A }],
    ),
  ),
];

const REDROP_MATCHUPS: MatchupItem[] = [
  mkMatchup(3, [
    { id: 50, pts: 10 },
    { id: 51, pts: 5 },
  ]),
  mkMatchup(4, [{ id: 50, pts: 20 }]),
  mkMatchup(5, [{ id: 50, pts: 100 }]),
  mkMatchup(6, [
    { id: 50, pts: 100 },
    { id: 51, pts: 10 },
  ]),
];

// Alice picks up "Flip Guy" (id 60) in week 2, then trades him to Bob in week 4 for "Return Guy"
// (id 61). Flip Guy: 10 + 10 while on Alice's roster (weeks 2–3); his week-4 50 belongs to Bob →
// the pickup is +20.00, not +70.00.
const TRADED_AWAY: TransactionItem[] = [
  atWeek(
    2,
    mkMove('fa-flip', 'free_agent', 100, [
      { id: '60', name: 'Flip Guy', roster: A },
    ]),
  ),
  atWeek(
    4,
    mkMove(
      'tr-flip',
      'trade',
      200,
      [
        { id: '60', name: 'Flip Guy', roster: B },
        { id: '61', name: 'Return Guy', roster: A },
      ],
      [
        { id: '60', name: 'Flip Guy', roster: A },
        { id: '61', name: 'Return Guy', roster: B },
      ],
    ),
  ),
];

const TRADED_AWAY_MATCHUPS: MatchupItem[] = [
  mkMatchup(2, [{ id: 60, pts: 10 }]),
  mkMatchup(3, [{ id: 60, pts: 10 }]),
  mkMatchup(4, [
    { id: 60, pts: 50 },
    { id: 61, pts: 7 },
  ]),
];

// Alice picks up "Blip" (id 70) and drops him again the same week (3): he never counts for her.
const SAME_WEEK: TransactionItem[] = [
  atWeek(
    3,
    mkMove('fa-blip', 'free_agent', 100, [
      { id: '70', name: 'Blip', roster: A },
    ]),
  ),
  atWeek(
    3,
    mkMove(
      'fa-unblip',
      'free_agent',
      200,
      [],
      [{ id: '70', name: 'Blip', roster: A }],
    ),
  ),
];

const SAME_WEEK_MATCHUPS: MatchupItem[] = [
  mkMatchup(3, [{ id: 70, pts: 12 }]),
  mkMatchup(4, [{ id: 70, pts: 12 }]),
];

// The week-3 Star/Role trade, after which Bob cuts Star Player in week 4. With ROS_MATCHUPS, Star
// Player counts only week 3 for Bob (30.00, not 70.00); Role Player keeps 25.00 → Bob by +5.00.
const TRADE_THEN_DROP: TransactionItem[] = [
  ...ROS_TRANSACTIONS,
  atWeek(
    4,
    mkMove(
      'fa-cut-star',
      'free_agent',
      1700000000001,
      [],
      [{ id: '10', name: 'Star Player', roster: B }],
    ),
  ),
];

/** The Top transactions tiles, in rendered order. */
async function topTiles(): Promise<HTMLElement[]> {
  const list = await screen.findByRole('list', { name: 'Top transactions' });
  return [...list.children] as HTMLElement[];
}

const tileFor = async (name: string) => {
  const tile = (await topTiles()).find((t) => t.textContent?.includes(name));
  expect(tile).toBeDefined();
  return tile!;
};

/** Waits until the wire has settled (it awaits every query), then asserts no highlight renders. */
async function expectNoTopTransactions() {
  await screen.findAllByText(/No transactions for this season\.|Star Player/);
  expect(
    screen.queryByRole('heading', { name: 'Top transactions' }),
  ).toBeNull();
}

const expectTopOrder = async (names: string) => {
  const tiles = await topTiles();
  const expected = names.split(', ');
  expect(tiles).toHaveLength(expected.length);
  expected.forEach((name, i) => expect(tiles[i].textContent).toContain(name));
};

defineFeature(feature, (test) => {
  const seePoints = async (pts: string) => {
    expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
  };
  const notSeePoints = (pts: string) => {
    expect(screen.queryByText(pts)).toBeNull();
  };
  const seeNet = async (value: string) => {
    expect(await screen.findByText(value)).toBeInTheDocument();
  };
  const selectFilter = async (label: string) => {
    await userEvent.click(screen.getByRole('button', { name: label }));
  };

  test('A pickup later dropped only counts its points while rostered', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a free-agent pickup that is later dropped, with matchup box scores',
      () => {
        server.use(
          leagueQuery({ TRANSACTIONS: REDROP, MATCHUPS: REDROP_MATCHUPS }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, selectFilter);
    then(/^I see the points "(.*)"$/, seePoints);
    and(/^I do not see the points "(.*)"$/, notSeePoints);
    // The dropped player keeps his full rest of season (week 6, after the cut, included).
    and(/^I see the points "(.*)"$/, seePoints);
    and(/^I see the net pickup value "(.*)"$/, seeNet);
    and(
      /^the top transaction for "(.*)" shows "(.*)"$/,
      async (player: string, value: string) => {
        expect((await tileFor(player)).textContent).toContain(value);
      },
    );
  });

  test('A traded player later dropped only counts his points while rostered', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a trade whose acquired player is later dropped, with matchup box scores',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: TRADE_THEN_DROP,
            MATCHUPS: ROS_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I see the points "(.*)"$/, seePoints);
    and(/^I do not see the points "(.*)"$/, notSeePoints);
    and(/^the trade winner is "(.*)" by "(.*)"$/, async (team, margin) => {
      expect(
        await screen.findByText(`${team} won by ${margin} pts`),
      ).toBeInTheDocument();
    });
    and(/^I see the side total label "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
  });

  test('A pickup later traded away stops counting at the trade week', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a free-agent pickup that is later traded away, with matchup box scores',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: TRADED_AWAY,
            MATCHUPS: TRADED_AWAY_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, selectFilter);
    then(/^I see the points "(.*)"$/, seePoints);
    and(/^I do not see the points "(.*)"$/, notSeePoints);
    and(/^I see the net pickup value "(.*)"$/, seeNet);
  });

  test('A pickup dropped in the same week counts nothing', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a free-agent pickup dropped again the same week, with matchup box scores',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: SAME_WEEK,
            MATCHUPS: SAME_WEEK_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, selectFilter);
    then(/^I see the points "(.*)"$/, seePoints);
    and(/^I see the net pickup value "(.*)"$/, seeNet);
  });

  test("The top transactions highlight ranks the season's best moves across types", ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a season of mixed transactions with matchup box scores is available',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: TOP_MIXED,
            MATCHUPS: TOP_MIXED_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^the top transactions are "(.*)" in order$/, expectTopOrder);
    and(/^the top transaction values are "(.*)"$/, async (values: string) => {
      const tiles = await topTiles();
      values
        .split(', ')
        .forEach((v, i) => expect(tiles[i].textContent).toContain(v));
    });
    const notIncluded = async (name: string) => {
      for (const tile of await topTiles()) {
        expect(tile.textContent).not.toContain(name);
      }
    };
    and(/^the top transactions do not include "(.*)"$/, notIncluded);
    and(/^the top transactions do not include "(.*)"$/, notIncluded);
    and(/^the top transactions do not include "(.*)"$/, notIncluded);
  });

  test('A trade tile credits the winning team', ({ given, when, then }) => {
    given(
      'a season of mixed transactions with matchup box scores is available',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: TOP_MIXED,
            MATCHUPS: TOP_MIXED_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(
      /^the top transaction for "(.*)" is credited to "(.*)" and shows "(.*)" and "(.*)"$/,
      async (player, team, label, opponent) => {
        const tile = await tileFor(player);
        expect(within(tile).getByText(team)).toBeInTheDocument();
        expect(within(tile).getByText(label)).toBeInTheDocument();
        expect(tile.textContent).toContain(opponent);
      },
    );
  });

  test('The top transactions highlight is independent of the type filter', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a season of mixed transactions with matchup box scores is available',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: TOP_MIXED,
            MATCHUPS: TOP_MIXED_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, async (label) => {
      await screen.findByRole('list', { name: 'Top transactions' });
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^the top transactions are "(.*)" in order$/, expectTopOrder);
  });

  test('Fewer than five eligible moves are shown, earlier first on a tie', ({
    given,
    when,
    then,
  }) => {
    given(
      'two equally valued pickups with matchup box scores are available',
      () => {
        server.use(
          leagueQuery({ TRANSACTIONS: TOP_TIE, MATCHUPS: TOP_TIE_MATCHUPS }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^the top transactions are "(.*)" in order$/, expectTopOrder);
  });

  test('The top transactions highlight is hidden when nothing is eligible', ({
    given,
    when,
    then,
  }) => {
    given('a pure free-agent drop with matchup box scores is available', () => {
      server.use(
        leagueQuery({
          TRANSACTIONS: ROS_FA_PURE_DROP,
          MATCHUPS: ROS_FA_PURE_DROP_MATCHUPS,
        }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then('there is no top transactions highlight', expectNoTopTransactions);
  });

  test('The top transactions highlight is hidden when box scores fail to load', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a season of mixed transactions whose matchup box scores fail to load',
      () => {
        // Transactions load; matchups 500 (standings 404s, which is tolerated).
        server.use(
          http.get(`${API}/leagues/:id/query`, ({ request }) => {
            const queryType =
              new URL(request.url).searchParams.get('queryType') ?? '';
            if (queryType.startsWith('TRANSACTIONS')) {
              return HttpResponse.json({ data: TOP_MIXED });
            }
            return HttpResponse.json(
              { detail: 'Internal Server Error' },
              { status: queryType.startsWith('MATCHUPS') ? 500 : 404 },
            );
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then('there is no top transactions highlight', expectNoTopTransactions);
    and(/^I see the received player "(.*)"$/, async (name) => {
      expect(
        (await screen.findAllByText(name, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
  });

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

  test("A free-agent add-and-drop shows each player's points and the net pickup value", ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a free-agent add-and-drop with matchup box scores is available',
      () => {
        server.use(
          leagueQuery({
            TRANSACTIONS: ROS_FA_ADD_DROP,
            MATCHUPS: ROS_FA_ADD_DROP_MATCHUPS,
          }),
        );
      },
    );
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    and(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    and(/^I see the net pickup value "(.*)"$/, async (value) => {
      expect(await screen.findByText(value)).toBeInTheDocument();
    });
    and(/^I see the points column header "(.*)"$/, async (note) => {
      expect(
        (await screen.findAllByText(note, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
    // Pickup Hero's week-2 (pre-move) 100 points must be excluded; 160.00 would mean it wasn't.
    and(/^I do not see the points "(.*)"$/, (pts) => {
      expect(screen.queryByText(pts)).toBeNull();
    });
  });

  test("A pure free-agent add shows the added player's points and its net pickup value", ({
    given,
    when,
    then,
    and,
  }) => {
    given('a pure free-agent add with matchup box scores is available', () => {
      server.use(
        leagueQuery({
          TRANSACTIONS: ROS_FA_PURE_ADD,
          MATCHUPS: ROS_FA_PURE_ADD_MATCHUPS,
        }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    // A pure add's net is just the added total (nothing dropped).
    and(/^I see the net pickup value "(.*)"$/, async (value) => {
      expect(await screen.findByText(value)).toBeInTheDocument();
    });
  });

  test("A pure free-agent drop shows the dropped player's points and its net pickup value", ({
    given,
    when,
    then,
    and,
  }) => {
    given('a pure free-agent drop with matchup box scores is available', () => {
      server.use(
        leagueQuery({
          TRANSACTIONS: ROS_FA_PURE_DROP,
          MATCHUPS: ROS_FA_PURE_DROP_MATCHUPS,
        }),
      );
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    and(/^I select the "(.*)" filter$/, async (label) => {
      await userEvent.click(screen.getByRole('button', { name: label }));
    });
    then(/^I see the points "(.*)"$/, async (pts) => {
      expect((await screen.findAllByText(pts)).length).toBeGreaterThan(0);
    });
    // A pure drop's net is the negative of the dropped total (nothing added).
    and(/^I see the net pickup value "(.*)"$/, async (value) => {
      expect(await screen.findByText(value)).toBeInTheDocument();
    });
  });

  test('A free-agent move renders without points when box scores are unavailable', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'a free-agent add-and-drop with no matchup box scores is available',
      () => {
        // No MATCHUPS key → the matchups query 404s, degrading silently to no points.
        server.use(leagueQuery({ TRANSACTIONS: ROS_FA_ADD_DROP }));
      },
    );
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
    and('there is no net pickup value', () => {
      expect(screen.queryByText('Net pickup value')).toBeNull();
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

  test('ESPN shows the historical-transactions disclaimer', ({
    given,
    when,
    then,
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
    then(/^I see the disclaimer "(.*)"$/, async (text) => {
      expect(
        (await screen.findAllByText(text, { exact: false })).length,
      ).toBeGreaterThan(0);
    });
  });

  test('Sleeper does not show the ESPN disclaimer', ({ given, when, then }) => {
    given('transactions data is available', () => {
      server.use(leagueQuery({ TRANSACTIONS }));
    });
    when('I open the transactions page', async () => {
      await renderRoute(<Transactions />, { route: '/transactions', league });
    });
    then(/^I do not see the disclaimer "(.*)"$/, async (text) => {
      // Wait for the page to render (the summary label always appears) before
      // asserting the ESPN-only disclaimer is absent.
      await screen.findByText('Summary');
      expect(screen.queryByText(text, { exact: false })).toBeNull();
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
