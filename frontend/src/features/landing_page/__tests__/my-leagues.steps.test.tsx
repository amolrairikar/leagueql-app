import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { delay, http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import LeagueQLLanding from '../landing-page';

import type { MyLeague } from '@/components/api/types';
import { setClerkState } from '@/test/clerk-mock';
import { API, leagueMetadataError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/landing_page/__tests__/my-leagues.feature',
);

const HOURS_AGO = (h: number) =>
  new Date(Date.now() - h * 60 * 60 * 1000).toISOString();

const LEAGUES: MyLeague[] = [
  {
    league_id: '1048',
    platform: 'SLEEPER',
    league_name: 'The Dynasty Bowl',
    seasons: ['2019', '2020', '2021', '2022', '2023', '2024', '2025'],
    updated_at: HOURS_AGO(2),
    migrated_from: null,
    espn_reauth_required: false,
  },
  {
    league_id: '555',
    platform: 'ESPN',
    league_name: 'Office League',
    seasons: ['2017', '2018'],
    updated_at: HOURS_AGO(48),
    migrated_from: null,
    espn_reauth_required: true,
  },
  {
    league_id: '777',
    platform: 'YAHOO',
    league_name: 'Fam Fantasy',
    seasons: ['2021', '2022'],
    updated_at: HOURS_AGO(200),
    migrated_from: 'ESPN',
    espn_reauth_required: false,
  },
];

const VIEW_MY_LEAGUES = /^View My Leagues/;

function myLeaguesReturn(leagues: MyLeague[]) {
  server.use(
    http.get(`${API}/me/leagues`, () =>
      HttpResponse.json({ detail: 'Found leagues', data: leagues }),
    ),
  );
}

function myLeaguesFail(status: number) {
  server.use(
    http.get(`${API}/me/leagues`, () =>
      HttpResponse.json({ detail: 'Not allowed' }, { status }),
    ),
  );
}

async function openLanding() {
  // The landing page fetches a live league count from a hardcoded URL; stub it.
  server.use(
    http.get('https://api.leagueql.com/counts', () =>
      HttpResponse.json({ leagueCount: 3 }),
    ),
  );
  await renderRoute(
    <Routes>
      <Route path="/" element={<LeagueQLLanding />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/' },
  );
}

function myLeaguesButton() {
  return screen.getByRole('button', { name: VIEW_MY_LEAGUES });
}

async function clickButton(name: string) {
  const user = userEvent.setup();
  const button =
    name === 'View My Leagues'
      ? myLeaguesButton()
      : await screen.findByRole('button', { name });
  await user.click(button);
}

function panel() {
  const el = document.getElementById('my-leagues-panel');
  if (!el) throw new Error('My leagues panel is not open');
  return el;
}

async function leagueRow(name: string) {
  const label = await within(panel()).findByText(name);
  const row = label.closest('li');
  if (!row) throw new Error(`No row for ${name}`);
  return row;
}

async function seeError(text: string) {
  expect(await screen.findByText(text)).toBeTruthy();
}

function expectExpanded(expanded: boolean) {
  expect(myLeaguesButton().getAttribute('aria-expanded')).toBe(
    String(expanded),
  );
}

defineFeature(feature, (test) => {
  test('The button is hidden when signed out', ({ given, when, then }) => {
    given('I am signed out', () => {
      setClerkState({ isSignedIn: false, user: null });
    });
    when('I open the landing page', openLanding);
    then('there is no "View My Leagues" button', () => {
      expect(
        screen.queryByRole('button', { name: VIEW_MY_LEAGUES }),
      ).toBeNull();
    });
  });

  test('Expanding and collapsing the panel', ({ given, when, then, and }) => {
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('the "View My Leagues" button is expanded', () =>
      expectExpanded(true),
    );
    and(/^I see the league "(.*)"$/, async (name: string) => {
      await leagueRow(name);
    });
    when('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('the "View My Leagues" button is collapsed', () =>
      expectExpanded(false),
    );
    and(/^I do not see the league "(.*)"$/, (name: string) => {
      expect(screen.queryByText(name)).toBeNull();
    });
  });

  test('Leagues are listed in API order with their details', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then(/^the leagues are listed in order "(.*)"$/, async (names: string) => {
      await leagueRow('The Dynasty Bowl');
      const rows = within(panel()).getAllByRole('button', {
        name: /Open|Loading/,
      });
      expect(rows.map((r) => r.textContent)).toEqual(
        names
          .split(', ')
          .map((n) => expect.stringContaining(n) as unknown as string),
      );
    });
    and(
      /^the league "(.*)" shows "(.*)"$/,
      async (name: string, text: string) => {
        expect((await leagueRow(name)).textContent).toContain(text);
      },
    );
    and(
      /^the league "(.*)" shows "(.*)"$/,
      async (name: string, text: string) => {
        expect((await leagueRow(name)).textContent).toContain(text);
      },
    );
    and(
      /^the league "(.*)" shows a "(.*)" flag$/,
      async (name: string, flag: string) => {
        expect(within(await leagueRow(name)).getByText(flag)).toBeTruthy();
      },
    );
    and(
      /^the league "(.*)" has no "(.*)" flag$/,
      async (name: string, flag: string) => {
        expect(within(await leagueRow(name)).queryByText(flag)).toBeNull();
      },
    );
    and(
      /^the "View My Leagues" button shows a count of (\d+)$/,
      (count: string) => {
        expect(within(myLeaguesButton()).getByText(count)).toBeTruthy();
      },
    );
    and(/^I see the hint "(.*)"$/, (hint: string) => {
      expect(panel().textContent).toContain(hint);
    });
  });

  test('A loading skeleton shows while the list is requested', ({
    given,
    when,
    then,
    and,
  }) => {
    given('my leagues request is still in flight', () => {
      server.use(
        http.get(`${API}/me/leagues`, async () => {
          await delay('infinite');
          return HttpResponse.json({});
        }),
      );
    });
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('I see the leagues loading skeleton', async () => {
      expect(
        await screen.findByRole('list', { name: 'Loading your leagues' }),
      ).toBeTruthy();
    });
  });

  test('An empty list offers to connect a league', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I have no leagues', () => myLeaguesReturn([]));
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('I see "No leagues yet"', async () => {
      expect(await screen.findByText('No leagues yet')).toBeTruthy();
    });
    when('I click the empty state\'s "Connect Your League"', async () => {
      await userEvent
        .setup()
        .click(
          within(panel()).getByRole('button', { name: /Connect Your League/ }),
        );
    });
    then('the connect form is shown', () => {
      expect(screen.getByPlaceholderText('League ID')).toBeTruthy();
    });
    and('the "View My Leagues" button is collapsed', () =>
      expectExpanded(false),
    );
  });

  test('A server error is shown inline and can be retried', ({
    given,
    when,
    then,
  }) => {
    given('my leagues request fails with status 500', () => myLeaguesFail(500));
    when('I open the landing page', openLanding);
    when('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then(
      'I see the error "Couldn\'t load your leagues. Check your connection and try again."',
      () =>
        seeError(
          "Couldn't load your leagues. Check your connection and try again.",
        ),
    );
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    when('I click "Try again"', () => clickButton('Try again'));
    then('I see the league "The Dynasty Bowl"', async () => {
      await leagueRow('The Dynasty Bowl');
    });
  });

  test("A client error shows the API's message", ({ given, when, then }) => {
    given('my leagues request fails with status 403', () => myLeaguesFail(403));
    when('I open the landing page', openLanding);
    when('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('I see the error "Not allowed"', () => seeError('Not allowed'));
  });

  test('Opening a league stores it and goes home', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    and('opening a league succeeds', () => {
      server.use(
        http.get(`${API}/leagues/:id`, () =>
          HttpResponse.json({
            detail: 'Found league',
            data: { seasons: ['2017', '2018'], league_name: 'Office League' },
          }),
        ),
      );
    });
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    and('I click the league "Office League"', async () => {
      await userEvent
        .setup()
        .click(within(await leagueRow('Office League')).getByRole('button'));
    });
    then('I land on the league home page', async () => {
      expect(await screen.findByText('HOME PAGE')).toBeTruthy();
    });
    and(
      'the selected league is "555" on "ESPN" with seasons "2017,2018"',
      () => {
        expect(window.localStorage.getItem('leagueId')).toBe('555');
        expect(window.localStorage.getItem('leaguePlatform')).toBe('ESPN');
        expect(window.localStorage.getItem('leagueSeasons')).toBe(
          JSON.stringify(['2017', '2018']),
        );
      },
    );
  });

  test('A failure opening a league is shown inline', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    and('opening a league fails with status 403', () => {
      server.use(leagueMetadataError(403));
    });
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    and('I click the league "Office League"', async () => {
      await userEvent
        .setup()
        .click(within(await leagueRow('Office League')).getByRole('button'));
    });
    then('I see the error "Not a member of this league"', () =>
      seeError('Not a member of this league'),
    );
    and('I am still on the landing page', () => {
      expect(screen.queryByText('HOME PAGE')).toBeNull();
      expect(panel()).toBeTruthy();
    });
  });

  test('The panel and the connect form are mutually exclusive', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I have leagues', () => myLeaguesReturn(LEAGUES));
    when('I open the landing page', openLanding);
    and('I click "View My Leagues"', () => clickButton('View My Leagues'));
    and('I click the hero "Connect Your League"', async () => {
      await userEvent
        .setup()
        .click(
          screen.getAllByRole('button', { name: /Connect Your League/ })[0],
        );
    });
    then('the connect form is shown', () => {
      expect(screen.getByPlaceholderText('League ID')).toBeTruthy();
    });
    and('the "View My Leagues" button is collapsed', () =>
      expectExpanded(false),
    );
    when('I click "View My Leagues"', () => clickButton('View My Leagues'));
    then('the connect form is not shown', () => {
      expect(screen.queryByPlaceholderText('League ID')).toBeNull();
    });
    and('the "View My Leagues" button is expanded', () => expectExpanded(true));
  });
});
