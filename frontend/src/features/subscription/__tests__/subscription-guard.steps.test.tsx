import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { Route, Routes } from 'react-router-dom';

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

const FEATURE_FLAG = 'paywall_test_feature';

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
  test('An active subscription renders the gated page', ({
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

  test('An expired subscription shows the inline paywall', ({
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

  test('From the paywall a user can return to the dashboard', ({
    given,
    when,
    then,
  }) => {
    given('the current league subscription has expired', () => {
      server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
    });
    when(
      'I open a gated page behind the guard and click back to dashboard',
      async () => {
        const user = userEvent.setup();
        await renderRoute(
          <Routes>
            <Route
              path="/premium"
              element={
                <SubscriptionGuard featureFlag={FEATURE_FLAG}>
                  <div>Protected analytics</div>
                </SubscriptionGuard>
              }
            />
            <Route path="/home" element={<div>HOME PAGE</div>} />
          </Routes>,
          { route: '/premium', league },
        );
        await user.click(
          await screen.findByRole('button', { name: /back to dashboard/i }),
        );
      },
    );
    then('I am routed to the home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('Billing disabled renders the page without a paywall (FE-026)', ({
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
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test("The feature's paywall flag disabled renders the page without a paywall (FE-026)", ({
    given,
    and,
    when,
    then,
  }) => {
    given('the feature paywall flag is disabled', () => {
      setFlagsForTesting({ billing: true, paywall_test_feature: false });
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
