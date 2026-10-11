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

// A finalized season whose title game was matchup period 15 (two-week playoff rounds),
// not week 17: Bob beat Alice in the "Finals". Bob has a final_rank; Alice has none, so
// her 2nd-place finish must come from losing the final.
const EARLY_FINAL_STANDINGS = STANDINGS.map((s) =>
  s.owner_id === 'uA'
    ? { ...s, final_rank: null, champion: 'No' }
    : { ...s, final_rank: 1, champion: 'Yes' },
);
const EARLY_FINAL_MATCHUPS: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]),
  {
    ...(MATCHUPS[0] as MatchupItem),
    week: '15',
    team_a_score: 110,
    team_b_score: 125,
    playoff_tier_type: 'WINNERS_BRACKET',
    playoff_round: 'Finals',
    winner: '2',
    loser: '1',
  },
];

// The same Alice-vs-Bob season repeated for 2023, so Alice has two expandable
// season cards.
const TWO_SEASON_STANDINGS = [
  ...STANDINGS.map((s) => ({ ...s, season: '2023' })),
  ...STANDINGS,
];
const TWO_SEASON_MATCHUPS: MatchupItem[] = [
  ...(MATCHUPS as MatchupItem[]).map((m) => ({ ...m, season: '2023' })),
  ...(MATCHUPS as MatchupItem[]),
];

const seasonButton = (year: string) =>
  screen.findByRole('button', { name: new RegExp(year) });

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
        const panel = await screen.findByRole('region', { name: /2024/ });
        // Played week-1 score cell (130.0–120.0) renders.
        expect(within(panel).getByText(/130\.0.120\.0/)).toBeInTheDocument();
        // The unplayed 0-0 week has no score cell (0.0–0.0) in the schedule.
        expect(within(panel).queryByText(/0\.0.0\.0/)).toBeNull();
      },
    );
  });

  test('Expanding a season shows its schedule inline', ({
    given,
    when,
    and,
    then,
  }) => {
    const user = userEvent.setup();
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    and('I open the 2024 season schedule', async () => {
      await user.click(await seasonButton('2024'));
    });
    then(
      'the 2024 season is expanded with its schedule shown inline',
      async () => {
        expect(await seasonButton('2024')).toHaveAttribute(
          'aria-expanded',
          'true',
        );
        const panel = await screen.findByRole('region', { name: /2024/ });
        expect(within(panel).getByText('Team Bob')).toBeInTheDocument();
        expect(within(panel).getByText(/130\.0.120\.0/)).toBeInTheDocument();
      },
    );
    and('no dialog is open', () => {
      expect(screen.queryByRole('dialog')).toBeNull();
    });
  });

  test('Clicking an expanded season again collapses it', ({
    given,
    when,
    and,
    then,
  }) => {
    const user = userEvent.setup();
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    and('I open the 2024 season schedule', async () => {
      await user.click(await seasonButton('2024'));
      await screen.findByRole('region', { name: /2024/ });
    });
    and('I click the 2024 season again', async () => {
      await user.click(await seasonButton('2024'));
    });
    then(
      'the 2024 season is collapsed and its schedule is hidden',
      async () => {
        expect(await seasonButton('2024')).toHaveAttribute(
          'aria-expanded',
          'false',
        );
        expect(screen.queryByRole('region', { name: /2024/ })).toBeNull();
        expect(screen.queryByText(/130\.0.120\.0/)).toBeNull();
      },
    );
  });

  test('Several seasons stay expanded', ({ given, when, and, then }) => {
    const user = userEvent.setup();
    given('manager history data for the 2023 and 2024 seasons', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: TWO_SEASON_STANDINGS,
          MATCHUPS: TWO_SEASON_MATCHUPS,
        }),
      );
    });
    when('I open the manager history page for both seasons', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: { ...LEAGUE, seasons: ['2023', '2024'] },
      });
    });
    and('I open the 2024 season schedule', async () => {
      await user.click(await seasonButton('2024'));
    });
    and('I open the 2023 season schedule', async () => {
      await user.click(await seasonButton('2023'));
    });
    then('both the 2023 and 2024 seasons are expanded', async () => {
      for (const year of ['2023', '2024']) {
        expect(await seasonButton(year)).toHaveAttribute(
          'aria-expanded',
          'true',
        );
        expect(
          await screen.findByRole('region', { name: new RegExp(year) }),
        ).toBeInTheDocument();
      }
    });
  });

  test('Selecting a game shows its box score inside the season', ({
    given,
    when,
    and,
    then,
  }) => {
    const user = userEvent.setup();
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    and('I open the 2024 season schedule', async () => {
      await user.click(await seasonButton('2024'));
    });
    and('I select the week 1 game', async () => {
      const panel = await screen.findByRole('region', { name: /2024/ });
      await user.click(within(panel).getByText(/130\.0.120\.0/));
    });
    then('the week 1 box score is shown inside the 2024 season', async () => {
      const panel = await screen.findByRole('region', { name: /2024/ });
      // Starters from both sides of the week-1 box score render in the card.
      expect(
        await within(panel).findByText('Pat Quarterback'),
      ).toBeInTheDocument();
      expect(within(panel).getByText('Quincy Back')).toBeInTheDocument();
      expect(screen.queryByRole('dialog')).toBeNull();
    });
  });

  test('An in-progress season shows the current standings position, not rank 0', ({
    given,
    when,
    then,
    and,
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
    and('the season card shows no playoff result pill', () => {
      // Playoff outcomes aren't settled for an in-progress season, so no pill
      // (not even the "Missed Playoffs" default) is shown.
      for (const label of [
        'Champion',
        'Runner-up',
        'Playoffs',
        'Missed Playoffs',
      ]) {
        expect(screen.queryByText(label)).toBeNull();
      }
    });
  });

  test('A finalized season keeps its playoff result pill', ({
    given,
    when,
    then,
  }) => {
    given('manager history data is available', () => {
      server.use(leagueQuery({ SEASON_STANDINGS: STANDINGS, MATCHUPS }));
    });
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^the season card shows the "(.*)" result pill$/, async (label) => {
      // Default manager Alice won the finalized 2024 season.
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
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

  test('Runner-up of an early final', ({ given, when, then, and }) => {
    given(
      /^manager history data where Alice lost a "Finals" game played in matchup period 15$/,
      () => {
        server.use(
          leagueQuery({
            SEASON_STANDINGS: EARLY_FINAL_STANDINGS,
            MATCHUPS: EARLY_FINAL_MATCHUPS,
          }),
        );
      },
    );
    when('I open the manager history page', async () => {
      await renderRoute(<ManagerHistory />, {
        route: '/manager_history',
        league: LEAGUE,
      });
    });
    then(/^the season card shows the "(.*)" result pill$/, async (label) => {
      // Default manager Alice lost the 2024 final.
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^the season card shows the finish "(.*)"$/, (finish) => {
      expect(screen.getAllByText(finish).length).toBeGreaterThan(0);
    });
  });
});
