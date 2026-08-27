import { act, fireEvent, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import HomePage from '../../home_page/home-page';
import LeagueQLLanding from '../../landing_page/landing-page';
import PlayoffBracket from '../../playoff_bracket/playoff-bracket';
import Transactions from '../../transactions/transactions';

import { isDemoMode } from '@/lib/cookie-handler';
import {
  DEMO_LEAGUE_ID,
  DEMO_PLATFORM,
  DEMO_SEASONS,
} from '@/lib/demo-constants';
import { renderRoute, setDemoMode } from '@/test/render';

const feature = loadFeature('src/features/demo/__tests__/demo-mode.feature');

defineFeature(feature, (test) => {
  test('The dashboard renders from fixtures without any network call', ({
    given,
    when,
    then,
  }) => {
    // No MSW handlers are registered; setup.ts uses onUnhandledRequest: 'error',
    // so any live fetch would fail the test — proving demo mode is fixture-only.
    given('demo mode is active', () => {
      setDemoMode();
    });
    when('I open the home dashboard in demo mode', async () => {
      await renderRoute(<HomePage />, {
        route: '/home',
        league: {
          leagueId: DEMO_LEAGUE_ID,
          platform: DEMO_PLATFORM,
          seasons: DEMO_SEASONS,
        },
      });
    });
    then(/^I see the headline stat "(.*)"$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
  });

  test('The Sleeper-only Transactions page renders demo fixtures', ({
    given,
    when,
    then,
  }) => {
    // As above, no MSW handlers are registered, so the demo fixtures (including
    // the TRANSACTIONS#2025 bucket) are the only possible data source.
    given('demo mode is active', () => {
      setDemoMode();
    });
    when('I open the transactions page in demo mode', async () => {
      await renderRoute(<Transactions />, {
        route: '/transactions',
        league: {
          leagueId: DEMO_LEAGUE_ID,
          platform: DEMO_PLATFORM,
          seasons: DEMO_SEASONS,
        },
      });
    });
    then('I see a transaction card for the 2025 demo season', async () => {
      // The demo dataset is deterministic (seed=42) and contains trades, so the
      // singular "Trade" card label is present (distinct from the "Trades" filter
      // button / summary column).
      const cards = await screen.findAllByText('Trade');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  test('The playoff bracket page offers a Bracket / Playoff Race toggle', ({
    given,
    when,
    then,
  }) => {
    // Uses the committed demo dataset (no MSW): the 2025 demo season is completed,
    // so the bracket renders and the demo-only toggle can switch to the predictor.
    given('demo mode is active', () => {
      setDemoMode();
    });
    when('I open the playoff bracket page in demo mode', async () => {
      await renderRoute(<PlayoffBracket />, {
        route: '/playoff_bracket',
        league: {
          leagueId: DEMO_LEAGUE_ID,
          platform: DEMO_PLATFORM,
          seasons: DEMO_SEASONS,
        },
      });
    });
    then(/^I see the "(.*)" toggle$/, async (label) => {
      expect(
        await screen.findByRole('button', { name: label }),
      ).toBeInTheDocument();
    });
    when('I switch to the Playoff Race view', async () => {
      const toggle = await screen.findByRole('button', {
        name: 'Playoff Race',
      });
      // The predictor mounts and loads demo fixtures via `use(promise)`, which
      // React 19 only flushes inside an act scope.
      await act(async () => {
        fireEvent.click(toggle);
        await Promise.resolve();
      });
    });
    then(/^I see the predictor heading "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('Returning to the landing page exits demo mode', ({
    given,
    when,
    then,
  }) => {
    // The landing page is never part of the demo experience, so mounting it clears
    // the demo_mode cookie regardless of how the user got there (header link, back
    // button, direct visit) — not just via the sidebar "Exit Demo" button.
    given('demo mode is active', () => {
      setDemoMode();
      expect(isDemoMode()).toBe(true);
    });
    when('I open the landing page', async () => {
      await renderRoute(<LeagueQLLanding />, { route: '/' });
    });
    then('demo mode is no longer active', () => {
      expect(isDemoMode()).toBe(false);
    });
  });
});
