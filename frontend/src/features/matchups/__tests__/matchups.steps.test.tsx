import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import Matchups from '../matchups';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS, WEEKLY_STANDINGS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/matchups/__tests__/matchups.feature');

/** Clones the base fixture matchup into a specific week with the given scores. */
const forWeek = (
  week: number,
  aScore: number,
  bScore: number,
): MatchupItem => ({
  ...MATCHUPS[0],
  week: String(week),
  team_a_score: aScore,
  team_b_score: bScore,
});

defineFeature(feature, (test) => {
  test('Matchups render when data loads', ({ given, when, then }) => {
    given('matchup data is available', () => {
      server.use(leagueQuery({ MATCHUPS, WEEKLY_STANDINGS }));
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the matchup data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('An in-progress season hides future weeks past the current week', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'an in-progress season with played weeks 1-2 and unplayed weeks 3-4',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [
              forWeek(1, 130, 120),
              forWeek(2, 110, 140),
              forWeek(3, 0, 0),
              forWeek(4, 0, 0),
            ],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    then(/^I see the week button "(.*)"$/, async (label) => {
      expect(await screen.findByRole('button', { name: label })).toBeTruthy();
    });
    and(/^I do not see the week button "(.*)"$/, (label) => {
      expect(screen.queryByRole('button', { name: label })).toBeNull();
    });
  });

  test('A live-week matchup opens the matchup preview', ({
    given,
    when,
    then,
  }) => {
    given(
      'an in-progress season with a played week 1 and a live week 2',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [forWeek(1, 120, 100), forWeek(2, 0, 0)],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    then('I see the matchup preview', async () => {
      expect(await screen.findByText('Win probability')).toBeTruthy();
      expect(screen.getByText('Top scorers this season')).toBeTruthy();
    });
  });

  test('Each matchup preview card scrolls horizontally on its own', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'an in-progress season with a played week 1 and a live week 2',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [forWeek(1, 120, 100), forWeek(2, 0, 0)],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    then(
      'each preview card is its own horizontally scrollable container',
      async () => {
        await screen.findByText('Win probability');
        const cards = screen.getAllByTestId('matchup-preview-card');
        // Hero, head to head, recent form, points by week, top scorers.
        expect(cards).toHaveLength(5);
        // jsdom has no layout, so assert the overflow classes that enable it.
        for (const card of cards) {
          expect(card.className).toContain('overflow-x-auto');
          expect((card.firstElementChild as HTMLElement).className).toContain(
            'min-w-fit',
          );
        }
        const recentForm = screen
          .getByText('Recent form')
          .closest('[data-testid="matchup-preview-card"]');
        expect(recentForm?.contains(screen.getByText('Win probability'))).toBe(
          false,
        );
      },
    );
    and('the recent form usernames can wrap to fit the card', () => {
      const recentForm = screen
        .getByText('Recent form')
        .closest('[data-testid="matchup-preview-card"]')!;
      const wrapping = recentForm.querySelectorAll(
        '[class*="overflow-wrap:anywhere"]',
      );
      expect(wrapping).toHaveLength(2);
    });
    and('the close button sits outside every scrollable card', () => {
      const close = screen.getByRole('button', { name: 'Close preview' });
      for (const card of screen.getAllByTestId('matchup-preview-card')) {
        expect(card.contains(close)).toBe(false);
      }
    });
  });

  test('Top scorers stack by team on mobile', ({ given, when, then, and }) => {
    given(
      'an in-progress season with a played week 1 and a live week 2',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [forWeek(1, 120, 100), forWeek(2, 0, 0)],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    // The Top Scorers card's team columns live in the grid after its label.
    const scorersGrid = (): HTMLElement =>
      screen.getByText('Top scorers this season')
        .nextElementSibling as HTMLElement;
    then(
      'the top scorers are a single column on mobile and two columns from the sm breakpoint',
      async () => {
        await screen.findByText('Top scorers this season');
        // jsdom has no layout, so assert the responsive grid classes.
        const classes = scorersGrid().className.split(' ');
        expect(classes).toContain('grid-cols-1');
        expect(classes).toContain('sm:grid-cols-2');
      },
    );
    and(/^"(.*)"'s top scorers are listed above "(.*)"'s$/, (first, second) => {
      const [top, bottom] = Array.from(scorersGrid().children);
      expect(within(top as HTMLElement).getByText(first)).toBeTruthy();
      expect(within(bottom as HTMLElement).getByText(second)).toBeTruthy();
    });
  });

  test('A played matchup opens the box score', ({ given, when, then }) => {
    given(
      'an in-progress season with a played week 1 and a live week 2',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [forWeek(1, 120, 100), forWeek(2, 0, 0)],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the week 1 matchup', async () => {
      await userEvent.click(
        await screen.findByRole('button', { name: 'Wk 1' }),
      );
      await userEvent.click(await screen.findByText(/View box score/));
    });
    then('I see the box score', async () => {
      // The box score renders a "Total" row, unique to the box-score view.
      expect((await screen.findAllByText('Total')).length).toBeGreaterThan(0);
    });
  });

  test("The season's first week renders the preview without scores", ({
    given,
    when,
    then,
  }) => {
    given('the first week of a season with no games played', () => {
      server.use(
        leagueQuery({ MATCHUPS: [forWeek(1, 0, 0)], WEEKLY_STANDINGS }),
      );
    });
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    then('I see the matchup preview', async () => {
      expect(await screen.findByText('Win probability')).toBeTruthy();
    });
  });

  test('Consistency is hidden early in the season', ({ given, when, then }) => {
    given(
      'an in-progress season with a played week 1 and a live week 2',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [forWeek(1, 120, 100), forWeek(2, 0, 0)],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    then('I do not see the head-to-head consistency stat', async () => {
      // Wait for the preview, then assert the σ row is absent (both teams share
      // the identical league-fallback σ after a single game).
      expect(await screen.findByText('Win probability')).toBeTruthy();
      expect(screen.queryByText('Consistency (σ)')).toBeNull();
    });
  });

  test("Consistency appears once each team's scoring differs", ({
    given,
    when,
    then,
  }) => {
    given(
      'an in-progress season with three played weeks and a live week 4',
      () => {
        server.use(
          leagueQuery({
            MATCHUPS: [
              forWeek(1, 120, 100),
              forWeek(2, 90, 110),
              forWeek(3, 130, 95),
              forWeek(4, 0, 0),
            ],
            WEEKLY_STANDINGS,
          }),
        );
      },
    );
    when('I open the matchups page', async () => {
      await renderRoute(<Matchups />, { route: '/matchups', league: LEAGUE });
    });
    when('I open the live-week matchup', async () => {
      await userEvent.click(await screen.findByText(/View matchup preview/));
    });
    then('I see the head-to-head consistency stat', async () => {
      expect(await screen.findByText('Consistency (σ)')).toBeTruthy();
    });
  });
});
