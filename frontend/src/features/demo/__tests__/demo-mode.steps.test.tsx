import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import HomePage from '../../home_page/home-page';

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
});
