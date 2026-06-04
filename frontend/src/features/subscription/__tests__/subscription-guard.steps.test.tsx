import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { SubscriptionGuard } from '../subscription-guard';

import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/subscription/__tests__/subscription-guard.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

defineFeature(feature, (test) => {
  test('An active subscription renders the gated page', ({
    given,
    when,
    then,
  }) => {
    given('the current league subscription ends in the future', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(30) }));
    });
    when('I open a gated page behind the subscription guard', async () => {
      await renderRoute(
        <SubscriptionGuard>
          <div>Protected analytics</div>
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('An expired subscription shows the inline paywall', ({
    given,
    when,
    then,
  }) => {
    given('the current league subscription has expired', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
    });
    when('I open a gated page behind the subscription guard', async () => {
      await renderRoute(
        <SubscriptionGuard>
          <div>Protected analytics</div>
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
