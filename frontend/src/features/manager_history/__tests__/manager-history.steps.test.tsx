import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import ManagerHistory from '../manager-history';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS, STANDINGS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

// Alice beat Bob in week 1; week 2 is an unplayed 0-0 placeholder between the same
// two managers. It must never appear as a game in Alice's season schedule.
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

// An in-progress season: ESPN reports `rankCalculatedFinal` (→ `final_rank`) as 0
// until the season is finalized, and no manager is champion yet. Each team's finish
// must fall back to its current standings position (wins, then points-for) — Alice
// (1-0) sits 1st, Bob (0-1) 2nd — never "0th" from ordinal(0).
const IN_PROGRESS_STANDINGS = STANDINGS.map((s) => ({
  ...s,
  final_rank: 0,
  champion: 'No',
}));

const feature = loadFeature(
  'src/features/manager_history/__tests__/manager-history.feature',
);

defineFeature(feature, (test) => {
  test('Manager history renders when data loads', ({ given, when, then }) => {
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test("An unplayed 0-0 week never appears in a manager's season schedule", ({
    given,
    when,
    and,
    then,
  }) => {
    const user = userEvent.setup();
    given('manager history data includes an unplayed 0-0 week', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: STANDINGS,
          MATCHUPS: MATCHUPS_WITH_UNPLAYED,
        }),
      );
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    and('I open the 2024 season schedule', async () => {
      // The default manager (Alice) lists a clickable 2024 season card.
      await user.click(await screen.findByRole('button', { name: /2024/ }));
    });
    then(
      'the schedule shows the played game but not the unplayed 0-0 game',
      async () => {
        const dialog = await screen.findByRole('dialog');
        // Played week-1 score cell (130.0–120.0) renders.
        expect(within(dialog).getByText(/130\.0.120\.0/)).toBeInTheDocument();
        // The unplayed 0-0 week has no score cell (0.0–0.0) in the schedule.
        expect(within(dialog).queryByText(/0\.0.0\.0/)).toBeNull();
      },
    );
  });

  test('An in-progress season shows the current standings position, not rank 0', ({
    given,
    when,
    then,
  }) => {
    given(
      'manager history data for an in-progress season with final_rank 0',
      () => {
        server.use(
          leagueQuery({ SEASON_STANDINGS: IN_PROGRESS_STANDINGS, MATCHUPS }),
        );
      },
    );
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(
      'the season card shows the current standings finish "1st" and never "0th"',
      async () => {
        // Default manager Alice (1-0) leads the in-progress season → 1st, derived
        // from the standings; final_rank 0 must never render as "0th".
        expect((await screen.findAllByText('1st')).length).toBeGreaterThan(0);
        expect(screen.queryByText(/0th/)).toBeNull();
      },
    );
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the manager history data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
