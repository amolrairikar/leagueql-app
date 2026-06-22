import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import AiRecap from '../ai-recap';

import { SubscriptionGuard } from '@/features/subscription/subscription-guard';
import { setFlagsForTesting } from '@/lib/feature-flags';
import {
  leagueMetadata,
  leagueQuery,
  leagueQueryError,
  server,
} from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/ai_recap/__tests__/ai-recap.feature');

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const RECAP = {
  season: '2024',
  week: '1',
  headline: 'Week 1: Alice Runs the Table',
  body: 'Alice steamrolled the league this week.',
  model: 'amazon.nova-lite-v1:0',
  generated_at: '2026-06-19T12:00:00+00:00',
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

async function openRecap() {
  await renderRoute(
    <AiRecap
      leagueId="100"
      platform="SLEEPER"
      season="2024"
      selectedWeek={1}
    />,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('A generated recap renders its headline and body', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a recap exists for the selected week', () => {
      server.use(leagueQuery({ RECAP: [RECAP] }));
    });
    when('I open the AI recap', openRecap);
    then(/^I see the recap headline "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and(/^I see the recap body text "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A week with no recap yet shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('no recap has been generated for the selected week', () => {
      // No RECAP key mapped → the query 404s, which the feature treats as empty.
      server.use(leagueQuery({ MATCHUPS: [] }));
    });
    when('I open the AI recap', openRecap);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the recap data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the AI recap', openRecap);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('An expired subscription shows the locked overlay without fetching data', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'the premium_feature flag is on and the league subscription has expired',
      () => {
        setFlagsForTesting({ billing: true, premium_feature: true });
        // No RECAP handler is registered. With MSW's onUnhandledRequest: 'error',
        // a data fetch would fail the test — so this scenario also proves the
        // gated component never fetches while locked.
        server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
      },
    );
    when('I open the gated AI recap', async () => {
      await renderRoute(
        <SubscriptionGuard
          featureFlag="premium_feature"
          featureLabel="AI weekly recap"
        >
          <AiRecap
            leagueId="100"
            platform="SLEEPER"
            season="2024"
            selectedWeek={1}
          />
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and('the AI recap is not rendered', () => {
      expect(
        screen.queryByText('Week 1: Alice Runs the Table'),
      ).not.toBeInTheDocument();
    });
  });
});
