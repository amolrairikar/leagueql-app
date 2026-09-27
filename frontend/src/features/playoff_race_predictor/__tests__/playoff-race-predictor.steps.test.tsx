import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import type { MatchupItem } from '@/components/api/types';
import PlayoffBracket from '@/features/playoff_bracket/playoff-bracket';
import { LEAGUE } from '@/test/fixtures';
import { leagueQuery, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/playoff_race_predictor/__tests__/playoff-race-predictor.feature',
);

/** A 2024 matchup between two teams; 0-0 scores mean unplayed. */
function game(
  aId: string,
  aOwner: string,
  bId: string,
  bOwner: string,
  week: number,
  aScore = 0,
  bScore = 0,
  tier = 'NONE',
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: aOwner,
    team_a_team_name: `Team ${aOwner}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: [],
    team_a_bench: [],
    team_a_primary_owner_id: `pid-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: bOwner,
    team_b_team_name: `Team ${bOwner}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: `pid-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: tier,
    playoff_round: tier === 'NONE' ? null : 'Finals',
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week: String(week),
    season: '2024',
  };
}

const SETTINGS = [
  {
    season: '2024',
    num_playoff_teams: 2,
    num_playoff_teams_assumed: false,
    playoff_week_start: 3,
    regular_season_weeks: 2,
  },
];

// Week 1 played, week 2 unplayed (0-0 placeholders) -> an in-progress season.
const IN_PROGRESS: MatchupItem[] = [
  game('t1', 'alice', 't2', 'bob', 1, 100, 90),
  game('t3', 'carol', 't4', 'dave', 1, 100, 80),
  game('t1', 'alice', 't3', 'carol', 2),
  game('t2', 'bob', 't4', 'dave', 2),
];

// Both regular-season weeks played -> the regular season is finished.
const FINISHED: MatchupItem[] = [
  game('t1', 'alice', 't2', 'bob', 1, 100, 90),
  game('t3', 'carol', 't4', 'dave', 1, 100, 80),
  game('t1', 'alice', 't3', 'carol', 2, 110, 95),
  game('t2', 'bob', 't4', 'dave', 2, 100, 80),
];

// A finished regular season plus a played postseason game, still no bracket rows.
const PLAYED_PLAYOFF: MatchupItem[] = [
  ...FINISHED,
  game('t1', 'alice', 't3', 'carol', 3, 120, 100, 'WINNERS_BRACKET'),
];

// Both regular-season weeks still unplayed: nothing is mathematically decided yet,
// so no clinching scenario qualifies and the section stays hidden.
const NOTHING_DECISIVE: MatchupItem[] = [
  game('t1', 'alice', 't2', 'bob', 1),
  game('t3', 'carol', 't4', 'dave', 1),
  game('t1', 'alice', 't3', 'carol', 2),
  game('t2', 'bob', 't4', 'dave', 2),
];

defineFeature(feature, (test) => {
  const open = async () => {
    await renderRoute(<PlayoffBracket />, {
      route: '/playoff_bracket',
      league: LEAGUE,
    });
  };

  test('The predictor renders for an in-progress season', ({
    given,
    when,
    then,
    and,
  }) => {
    given('an in-progress season with unplayed regular-season games', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: IN_PROGRESS,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
  });

  test('Picking a winner enables reset', ({ given, when, then }) => {
    given('an in-progress season with unplayed regular-season games', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: IN_PROGRESS,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^the "Reset picks" control is disabled$/, async () => {
      expect(
        await screen.findByRole('button', { name: /reset picks/i }),
      ).toBeDisabled();
    });
    when(/^I pick the winner "(.*)"$/, async (owner) => {
      const card = (
        await screen.findAllByRole('button', {
          name: new RegExp(owner, 'i'),
        })
      )[0];
      fireEvent.click(card);
    });
    then(/^the "Reset picks" control is enabled$/, () => {
      expect(
        screen.getByRole('button', { name: /reset picks/i }),
      ).toBeEnabled();
    });
  });

  test('The standings table shows a playoff-odds column', ({
    given,
    when,
    then,
    and,
  }) => {
    given('an in-progress season with unplayed regular-season games', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: IN_PROGRESS,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    // alice and carol are in the top 2 across every remaining outcome -> 100%.
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The projected standings break down per-seed odds and drop Win %', ({
    given,
    when,
    then,
    and,
  }) => {
    given('an in-progress season with unplayed regular-season games', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: IN_PROGRESS,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I do not see "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).toBeNull();
    });
  });

  test('A finished regular season with no bracket shows the empty state', ({
    given,
    when,
    then,
  }) => {
    given(
      "the latest season's regular season is finished with no bracket",
      () => {
        server.use(
          leagueQuery({
            PLAYOFF_BRACKET: [],
            MATCHUPS: FINISHED,
            WEEKLY_STANDINGS: [],
            LEAGUE_SETTINGS: SETTINGS,
          }),
        );
      },
    );
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('A played playoff game with no bracket shows the empty state', ({
    given,
    when,
    then,
  }) => {
    given('the latest season has a played playoff game but no bracket', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: PLAYED_PLAYOFF,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  const inProgress = (given: (s: string, cb: () => void) => void) =>
    given('an in-progress season with unplayed regular-season games', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: IN_PROGRESS,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });

  test('Clinching scenarios appear when a game is decisive', ({
    given,
    when,
    then,
    and,
  }) => {
    inProgress(given);
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('Clinching scenarios update when I pick a winner', ({
    given,
    when,
    then,
  }) => {
    inProgress(given);
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    when(/^I pick the winner "(.*)"$/, async (owner) => {
      const card = (
        await screen.findAllByRole('button', { name: new RegExp(owner, 'i') })
      )[0];
      fireEvent.click(card);
    });
    then(/^I no longer see "(.*)"$/, async (text) => {
      await waitFor(() => expect(screen.queryByText(text)).toBeNull());
    });
  });

  test('No clinching scenarios when nothing is decided', ({
    given,
    when,
    then,
    and,
  }) => {
    given('an early season with nothing decided', () => {
      server.use(
        leagueQuery({
          PLAYOFF_BRACKET: [],
          MATCHUPS: NOTHING_DECISIVE,
          WEEKLY_STANDINGS: [],
          LEAGUE_SETTINGS: SETTINGS,
        }),
      );
    });
    when('I open the playoff bracket page', open);
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I do not see "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).toBeNull();
    });
  });
  test("The week's matchups scroll horizontally with equal-width team cards", ({
    given,
    when,
    then,
    and,
  }) => {
    inProgress(given);
    when('I open the playoff bracket page', open);
    then(
      "the week's matchups are in a horizontally scrollable container",
      async () => {
        const card = await screen.findByTestId('predictor-matchups');
        // jsdom has no layout, so assert the classes that enable it.
        expect(card.className).toContain('overflow-x-auto');
        expect(within(card).getAllByText('vs').length).toBeGreaterThan(0);
      },
    );
    and(
      'the matchup rows are sized so every team card is the same width',
      () => {
        // max-content sizing (floored at the card width) makes each row's 1fr
        // team tracks resolve to the widest card instead of content-sized ones.
        const rows = screen.getByTestId('predictor-matchups')
          .firstElementChild as HTMLElement;
        const classes = rows.className.split(' ');
        expect(classes).toContain('w-max');
        expect(classes).toContain('min-w-full');
      },
    );
  });
  test('The projected standings freeze the Seed · Owner column', ({
    given,
    when,
    then,
    and,
  }) => {
    inProgress(given);
    when('I open the playoff bracket page', open);
    // jsdom has no layout, so assert the sticky/background classes.
    const classesOf = (el: Element) => el.className.split(' ');
    const ownerCells = () =>
      Array.from(
        screen
          .getByText('Seed · Owner')
          .closest('table')!
          .querySelectorAll('tbody tr td:first-child:not([colspan])'),
      );
    then(
      "the Seed · Owner header and every row's owner cell are frozen with an opaque background",
      async () => {
        const header = classesOf(await screen.findByText('Seed · Owner'));
        expect(header).toEqual(
          expect.arrayContaining(['sticky', 'left-0', 'bg-muted']),
        );
        const cells = ownerCells();
        expect(cells).toHaveLength(4);
        for (const cell of cells) {
          expect(classesOf(cell)).toEqual(
            expect.arrayContaining(['sticky', 'left-0', 'bg-card']),
          );
        }
      },
    );
    and(
      /^the frozen cells of the (\d+) playoff rows keep the playoff highlight$/,
      (count: string) => {
        const tinted = ownerCells().filter((c) =>
          classesOf(c).includes('from-primary/10'),
        );
        expect(tinted).toHaveLength(Number(count));
      },
    );
    and('the playoff line label is frozen', () => {
      expect(classesOf(screen.getByText('Playoff line'))).toContain('sticky');
    });
    and('the frozen column is capped on mobile with wrapping names', () => {
      const cells = [screen.getByText('Seed · Owner'), ...ownerCells()];
      for (const cell of cells) {
        expect(classesOf(cell)).toEqual(
          expect.arrayContaining(['w-67', 'sm:w-auto']),
        );
      }
      const names = screen
        .getAllByText(/^Team /)
        .filter((el) => el.closest('table'));
      expect(names.length).toBeGreaterThan(0);
      for (const name of names) {
        expect(classesOf(name.parentElement!)).toContain(
          '[overflow-wrap:anywhere]',
        );
      }
    });
  });
});
