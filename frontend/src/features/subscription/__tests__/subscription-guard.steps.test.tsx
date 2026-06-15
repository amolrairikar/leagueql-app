import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { SubscriptionGuard } from '../subscription-guard';

import { setFlagsForTesting } from '@/lib/feature-flags';
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

const FEATURE_FLAG = 'premium_feature';

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

async function openGatedPage() {
  await renderRoute(
    <SubscriptionGuard featureFlag={FEATURE_FLAG}>
      <div>Protected analytics</div>
    </SubscriptionGuard>,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('An active subscription renders the gated content', ({
    given,
    when,
    then,
  }) => {
    given('the current league subscription ends in the future', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(30) }));
    });
    when('I open a gated page behind the subscription guard', openGatedPage);
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('An expired subscription shows the locked overlay', ({
    given,
    when,
    then,
  }) => {
    given('the current league subscription has expired', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
    });
    when('I open a gated page behind the subscription guard', openGatedPage);
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('Billing disabled hides the premium section entirely (FE-026)', ({
    given,
    and,
    when,
    then,
  }) => {
    given('billing is disabled', () => {
      setFlagsForTesting({ billing: false });
    });
    and('the current league subscription has expired', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
    });
    when('I open a gated page behind the subscription guard', openGatedPage);
    then(/^the gated content "(.*)" is not shown$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  test("The feature's paywall flag disabled renders the page without a paywall (FE-026)", ({
    given,
    and,
    when,
    then,
  }) => {
    given('the feature paywall flag is disabled', () => {
      setFlagsForTesting({ billing: true, premium_feature: false });
    });
    and('the current league subscription has expired', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
    });
    when('I open a gated page behind the subscription guard', openGatedPage);
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
