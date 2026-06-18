import { screen, within } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import SeasonStandings from '../season-standings';

import { MATCHUPS, STANDINGS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/season_standings/__tests__/season-standings.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

/** The last cell of the standings row for `name` is the SoS column. */
async function sosCellFor(name: string): Promise<HTMLElement> {
  // The name also appears in the awards cards, so pick the occurrence that sits
  // inside a table row (the standings table).
  const row = (await screen.findAllByText(name))
    .map((el) => el.closest('tr'))
    .find((r): r is HTMLTableRowElement => r !== null)!;
  const cells = within(row).getAllByRole('cell');
  return cells[cells.length - 1];
}

defineFeature(feature, (test) => {
  test('Standings render when data loads', ({ given, when, then }) => {
    given('season standings data is available', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: STANDINGS,
          MATCHUPS,
          WEEKLY_STANDINGS: [],
        }),
      );
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('Strength of schedule reflects opponents faced', ({
    given,
    when,
    then,
    and,
  }) => {
    given('season standings data is available', () => {
      server.use(
        leagueQuery({
          SEASON_STANDINGS: STANDINGS,
          MATCHUPS,
          WEEKLY_STANDINGS: [],
        }),
      );
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    // Alice (win% 1.000) and Bob (win% 0.000) only played each other, so each
    // team's SoS is its single opponent's win%.
    then(
      /^the schedule strength for "(.*)" is "(.*)"$/,
      async (name, value) => {
        expect(await sosCellFor(name)).toHaveTextContent(value);
      },
    );
    and(/^the schedule strength for "(.*)" is "(.*)"$/, async (name, value) => {
      expect(await sosCellFor(name)).toHaveTextContent(value);
    });
  });

  test('Strength of schedule shows a dash when matchups are missing', ({
    given,
    when,
    then,
  }) => {
    given('season standings data is available but matchups are missing', () => {
      server.use(
        leagueQuery({ SEASON_STANDINGS: STANDINGS, WEEKLY_STANDINGS: [] }),
      );
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    then(
      /^the schedule strength for "(.*)" is "(.*)"$/,
      async (name, value) => {
        expect(await sosCellFor(name)).toHaveTextContent(value);
      },
    );
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the standings data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the standings page', async () => {
      await renderRoute(<SeasonStandings />, { route: '/standings', league });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
