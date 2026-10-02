import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { type DraftPickItem } from '../api-calls';
import DraftGrades from '../draft-grades';

import { DRAFT, LEAGUE } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/draft_grades/__tests__/draft-grades.feature',
);

// Builds a snake pick from the base fixture. Alice sorts first, so her picks
// are the ones shown by default.
const draftPick = (overrides: Partial<DraftPickItem>): DraftPickItem => ({
  ...DRAFT[0],
  ...overrides,
});

// An early-round RB bust for Alice, two better RBs Bob drafted right after it
// (one a keeper), and a round-5 kicker so round 1 clears BUST_ROUND_BUFFER.
const keeperDraft = ({ bustIsKeeper }: { bustIsKeeper: boolean }) => [
  draftPick({
    pick_id: 1,
    player_id: 'bust',
    player_name: 'Bust Back',
    position: 'RB',
    overall_pick_number: 1,
    round: 1,
    drafted_position_rank: 1,
    actual_position_rank: 11,
    draft_rank_delta: -10,
    total_points: 50,
    keeper: bustIsKeeper,
  }),
  draftPick({
    pick_id: 3,
    player_id: 'kept',
    player_name: 'Kept Runner',
    position: 'RB',
    overall_pick_number: 3,
    round: 2,
    drafted_position_rank: 2,
    actual_position_rank: 1,
    draft_rank_delta: 1,
    total_points: 250,
    keeper: true,
    owner_username: 'Bob',
    team_id: '2',
    team_name: 'Team Bob',
  }),
  draftPick({
    pick_id: 4,
    player_id: 'open',
    player_name: 'Open Runner',
    position: 'RB',
    overall_pick_number: 4,
    round: 2,
    drafted_position_rank: 3,
    actual_position_rank: 2,
    draft_rank_delta: 1,
    total_points: 150,
    owner_username: 'Bob',
    team_id: '2',
    team_name: 'Team Bob',
  }),
  draftPick({
    pick_id: 10,
    player_id: 'kicker',
    player_name: 'Late Kicker',
    position: 'K',
    overall_pick_number: 10,
    round: 5,
    draft_rank_delta: null,
    actual_position_rank: null,
    total_points: 100,
    vorp: null,
  }),
];

defineFeature(feature, (test) => {
  test('Draft grades render when data loads', ({ given, when, then }) => {
    given('draft grade data is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A pick with no scoring data renders without crashing', ({
    given,
    when,
    then,
  }) => {
    given('draft grade data is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the draft grade data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('Keepers are not suggested as alternatives', ({
    given,
    when,
    and,
    then,
  }) => {
    given("draft data where a bust's better alternative was a keeper", () => {
      server.use(leagueQuery({ DRAFT: keeperDraft({ bustIsKeeper: false }) }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
    });
    and("I show the bust's alternatives", async () => {
      // The desktop row and mobile card share open state; either toggle opens both.
      const [toggle] = await screen.findAllByText('Show alternatives');
      await userEvent.setup().click(toggle);
    });
    then(/^I see the alternative "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and(/^I do not see "(.*)"$/, (name) => {
      expect(screen.queryByText(name)).not.toBeInTheDocument();
    });
  });

  test('A keeper bust shows no alternatives', ({ given, when, then, and }) => {
    given('draft data where the bust pick was a keeper', () => {
      server.use(leagueQuery({ DRAFT: keeperDraft({ bustIsKeeper: true }) }));
    });
    when('I open the draft grades page', async () => {
      await renderRoute(<DraftGrades />, {
        route: '/draft_grades',
        league: LEAGUE,
      });
      await screen.findAllByText('Bust Back');
    });
    then(/^I do not see "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
    and(/^the busts count is "(.*)"$/, (count) => {
      const card = screen.getByText('Busts').closest('.bg-card');
      expect(within(card as HTMLElement).getByText(count)).toBeInTheDocument();
    });
  });
});
