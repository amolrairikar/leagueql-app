import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import HomePage from '../../home_page/home-page';
import Transactions from '../../transactions/transactions';

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
});
