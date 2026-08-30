import { act, fireEvent, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import MyTeam from '../my-team';

import { draftPick, game, player, standing } from './factories';

import type { Platform } from '@/components/api/types';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/my_team/__tests__/my-team.feature');

const STANDINGS = [
  standing({
    team_id: 't1',
    owner_username: 'Alice',
    team_name: 'Autobots',
    wins: 3,
    losses: 0,
    record: '3-0',
    win_pct: 1,
    games_played: 3,
    total_pf: 380,
    avg_pf: 126.7,
    win_pct_vs_league: 0.9,
  }),
  standing({
    team_id: 't2',
    owner_username: 'Bob',
    team_name: 'Decepticons',
    wins: 1,
    losses: 2,
    record: '1-2',
    win_pct: 0.333,
    games_played: 3,
    total_pf: 285,
    win_pct_vs_league: 0.4,
  }),
  standing({
    team_id: 't3',
    owner_username: 'Cara',
    team_name: 'Chargers',
    wins: 2,
    losses: 1,
    total_pf: 300,
  }),
  standing({
    team_id: 't4',
    owner_username: 'Dan',
    team_name: 'Dolphins',
    wins: 0,
    losses: 3,
    total_pf: 275,
  }),
];

const MATCHUPS = [
  game('t1', 't2', 130, 90, {
    week: 1,
    aStarters: [player(1, 10, 'RB')],
    aBench: [player(2, 40, 'RB')],
  }),
  game('t3', 't4', 100, 95, { week: 1 }),
  game('t1', 't3', 120, 100, { week: 2 }),
  game('t2', 't4', 100, 90, { week: 2 }),
  game('t1', 't4', 130, 90, { week: 3 }),
  game('t2', 't3', 95, 100, { week: 3 }),
];

const DRAFT = [
  draftPick({
    team_id: 't1',
    player_name: 'Bijan',
    round: 3,
    draft_rank_delta: 12,
    actual_position_rank: 6,
  }),
  draftPick({
    team_id: 't1',
    player_name: 'Andrews',
    round: 2,
    draft_rank_delta: -8,
  }),
];

const TRANSACTIONS = [
  {
    season: '2024',
    transaction_id: 'tx1',
    type: 'trade' as const,
    week: 1,
    created: 0,
    roster_ids: ['t1', 't2'],
    teams: [
      { roster_id: 't1', team_name: 'Autobots', display_name: 'Alice' },
      { roster_id: 't2', team_name: 'Decepticons', display_name: 'Bob' },
    ],
    adds: [
      {
        player_id: '99',
        player_name: 'Chase',
        position: 'WR',
        roster_id: 't1',
      },
      { player_id: '88', player_name: 'CMC', position: 'RB', roster_id: 't2' },
    ],
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  },
];

async function openMyTeam(platform: Platform) {
  await renderRoute(<MyTeam />, {
    league: { leagueId: '100', platform, seasons: ['2024'] },
  });
}

defineFeature(feature, (test) => {
  test('The report renders for a Sleeper team', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a Sleeper league with team data', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: STANDINGS,
          MATCHUPS,
          DRAFT,
          TRANSACTIONS,
        }),
      );
    });
    when('I open my team', () => openMyTeam('SLEEPER'));
    const seeSection = async (text: string) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    };
    then(/^I see "(.*)"$/, seeSection);
    and(/^I see the section "(.*)"$/, seeSection);
    and(/^I see the section "(.*)"$/, seeSection);
    and(/^I see the section "(.*)"$/, seeSection);
    and(/^I see the section "(.*)"$/, seeSection);
  });

  test('Selecting a different team re-filters the report', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a Sleeper league with team data', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: STANDINGS,
          MATCHUPS,
          DRAFT,
          TRANSACTIONS,
        }),
      );
    });
    when('I open my team', () => openMyTeam('SLEEPER'));
    and(/^I select the team "(.*)"$/, async (name) => {
      // Wait for the report (default: Alice) to render first.
      await screen.findByText('Autobots');
      const ownerId = STANDINGS.find(
        (s) => s.owner_username === name,
      )!.owner_id;
      const select = screen.getByLabelText('Select team');
      act(() => {
        fireEvent.change(select, { target: { value: ownerId } });
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('ESPN leagues gate the trade report', ({ given, when, then }) => {
    given('an ESPN league with team data', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS, DRAFT }));
    });
    when('I open my team', () => openMyTeam('ESPN'));
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the team data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open my team', () => openMyTeam('SLEEPER'));
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A season without data shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the season has no team data', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: [], MATCHUPS: [] }));
    });
    when('I open my team', () => openMyTeam('SLEEPER'));
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
