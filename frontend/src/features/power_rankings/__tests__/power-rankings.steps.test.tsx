import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import PowerRankings from '../power-rankings';

import type { MatchupItem } from '@/components/api/types';
import { LEAGUE, MATCHUPS } from '@/test/fixtures';
import { leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const NAMES: Record<string, string> = {
  '1': 'Amy',
  '2': 'Ben',
  '3': 'Cal',
  '4': 'Dee',
};

function game(
  week: number,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  tier = 'NONE',
): MatchupItem {
  return {
    ...(MATCHUPS[0] as MatchupItem),
    week: String(week),
    team_a_id: aId,
    team_a_display_name: NAMES[aId],
    team_a_team_name: `Team ${NAMES[aId]}`,
    team_a_score: aScore,
    team_a_starters: [],
    team_a_bench: [],
    team_b_id: bId,
    team_b_display_name: NAMES[bId],
    team_b_team_name: `Team ${NAMES[bId]}`,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    playoff_tier_type: tier,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
  };
}

// Amy wins every week and scores the most; Dee loses every week and scores the least.
const THREE_WEEKS: MatchupItem[] = [
  game(1, '1', 150, '2', 100),
  game(1, '3', 120, '4', 80),
  game(2, '1', 140, '3', 110),
  game(2, '2', 90, '4', 70),
  game(3, '1', 160, '4', 60),
  game(3, '2', 100, '3', 105),
];

const WITH_UNPLAYED_AND_PLAYOFFS: MatchupItem[] = [
  ...THREE_WEEKS,
  game(4, '1', 0, '2', 0),
  game(15, '4', 300, '1', 10, 'WINNERS_BRACKET'),
];

const NO_GAMES_PLAYED: MatchupItem[] = [game(1, '1', 0, '2', 0)];

const openPage = () =>
  renderRoute(<PowerRankings />, { route: '/power_rankings', league: LEAGUE });

/** The team names in table order, read from the visible rows. */
const rankedTeams = async () => {
  await screen.findByText('Team Amy');
  return screen
    .getAllByRole('row')
    .map(
      (row) => within(row).queryByText(/^Team (Amy|Ben|Cal|Dee)$/)?.textContent,
    )
    .filter((name): name is string => Boolean(name));
};

const feature = loadFeature(
  'src/features/power_rankings/__tests__/power-rankings.feature',
);

defineFeature(feature, (test) => {
  test('Rankings render for the latest week', ({ given, when, then, and }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    then(/^the week picker shows "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^the teams are ranked (.*)$/, async (list) => {
      const expected = [...list.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
      expect(await rankedTeams()).toEqual(expected);
    });
    and(/^the formula section "(.*)" is collapsed$/, async (heading) => {
      const toggle = await screen.findByRole('button', { name: heading });
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
      expect(screen.queryByText('Points scored')).not.toBeInTheDocument();
    });
  });

  test('Expanding the formula section', ({ given, when, then, and }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and(/^I expand the formula section "(.*)"$/, async (heading) => {
      await userEvent.click(
        await screen.findByRole('button', { name: heading }),
      );
    });
    then(/^I see the weights (.*)$/, async (list) => {
      const labels = [...list.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
      const section = await screen.findByRole('region', {
        name: 'How power rankings are calculated',
      });
      for (const label of labels) {
        expect(within(section).getByText(label)).toBeInTheDocument();
      }
      expect(within(section).getByText('35%')).toBeInTheDocument();
      expect(
        within(section).queryByText('How it\u2019s calculated'),
      ).not.toBeInTheDocument();
      expect(
        within(section).getByText(
          'Win percentage so far this season, multiplied by 100.',
        ),
      ).toBeInTheDocument();
      expect(
        within(section).getByRole('button', {
          name: 'How power rankings are calculated',
        }),
      ).toHaveAttribute('aria-expanded', 'true');
    });
    and(
      /^I see the scaling example "(.*)" with a scaled score of "(.*)"$/,
      async (heading, score) => {
        const section = await screen.findByRole('region', {
          name: 'How power rankings are calculated',
        });
        expect(
          within(section).getByRole('heading', { name: heading }),
        ).toBeInTheDocument();
        expect(within(section).getByText(score)).toBeInTheDocument();
        expect(within(section).getByText('Scaled score')).toBeInTheDocument();
      },
    );
  });

  test('Collapsing the formula section', ({ given, when, then, and }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and(/^I expand the formula section "(.*)"$/, async (heading) => {
      await userEvent.click(
        await screen.findByRole('button', { name: heading }),
      );
    });
    and(/^I collapse the formula section "(.*)"$/, async (heading) => {
      await userEvent.click(
        await screen.findByRole('button', { name: heading }),
      );
    });
    then(/^I do not see "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  test('Stepping back to an earlier week', ({ given, when, then, and }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and('I step to the previous week', async () => {
      await userEvent.click(
        await screen.findByRole('button', { name: 'Previous week' }),
      );
    });
    then(/^the week picker shows "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^Amy's record is "(.*)"$/, async (record) => {
      const row = (await screen.findByText('Team Amy')).closest('tr')!;
      expect(within(row).getByText(record)).toBeInTheDocument();
    });
  });

  test('The earliest week cannot be stepped back from', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and('I step to the previous week twice', async () => {
      const previous = await screen.findByRole('button', {
        name: 'Previous week',
      });
      await userEvent.click(previous);
      await userEvent.click(previous);
    });
    then(/^the week picker shows "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and('the previous week button is disabled', () => {
      expect(
        screen.getByRole('button', { name: 'Previous week' }),
      ).toBeDisabled();
    });
  });

  test('Expanding a team shows its breakdown', ({ given, when, then, and }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and(/^I expand "(.*)"$/, async (team) => {
      await userEvent.click(
        await screen.findByRole('button', { name: `Show details for ${team}` }),
      );
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('Collapsing a team hides its breakdown', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season with three played weeks', () => {
      server.use(leagueQuery({ MATCHUPS: THREE_WEEKS }));
    });
    when('I open the power rankings page', openPage);
    and(/^I expand "(.*)"$/, async (team) => {
      await userEvent.click(
        await screen.findByRole('button', { name: `Show details for ${team}` }),
      );
    });
    and(/^I collapse "(.*)"$/, async (team) => {
      await userEvent.click(
        await screen.findByRole('button', { name: `Hide details for ${team}` }),
      );
    });
    then(/^I do not see "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  test('Unplayed and playoff games are ignored', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season with an unplayed week and a playoff game', () => {
      server.use(leagueQuery({ MATCHUPS: WITH_UNPLAYED_AND_PLAYOFFS }));
    });
    when('I open the power rankings page', openPage);
    then(/^the week picker shows "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^the teams are ranked (.*)$/, async (list) => {
      const expected = [...list.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
      expect(await rankedTeams()).toEqual(expected);
    });
  });

  test('A season with no played games shows an empty message', ({
    given,
    when,
    then,
  }) => {
    given('a season with no played games', () => {
      server.use(leagueQuery({ MATCHUPS: NO_GAMES_PLAYED }));
    });
    when('I open the power rankings page', openPage);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline error', ({ given, when, then }) => {
    given('the matchups fail to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the power rankings page', openPage);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
