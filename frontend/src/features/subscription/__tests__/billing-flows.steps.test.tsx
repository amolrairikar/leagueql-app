import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, vi } from 'vitest';

import { ManageSubscriptionDialog } from '../manage-subscription-dialog';
import { SubscriptionRequired } from '../subscription-required';

import { leagueMetadata, postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/subscription/__tests__/billing-flows.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};
const STRIPE_URL = 'https://stripe.test/checkout/abc';

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

// jsdom's `location.assign` is non-configurable, so replace `window.location`
// wholesale with a stub exposing an `assign` mock, then restore it afterward.
const realLocation = window.location;
function mockNavigation() {
  const assign = vi.fn();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { assign, search: '', pathname: '/', href: 'http://localhost/' },
  });
  return assign;
}

defineFeature(feature, (test) => {
  let assignSpy: ReturnType<typeof vi.fn>;

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: realLocation,
    });
  });

  test('Subscribe redirects to Stripe Checkout', ({ given, when, then }) => {
    given('a checkout session will be created', () => {
      server.use(
        postJson('/leagues/100/checkout-session', {
          data: { url: STRIPE_URL },
        }),
      );
      assignSpy = mockNavigation();
    });
    when('I click Subscribe on the paywall', async () => {
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then('the browser is redirected to the Stripe URL', () => {
      expect(assignSpy).toHaveBeenCalledWith(STRIPE_URL);
    });
  });

  test('A 409 on checkout shows an inline error', ({ given, when, then }) => {
    given('checkout is rejected because a subscription already exists', () => {
      server.use(
        postJson(
          '/leagues/100/checkout-session',
          { detail: 'A subscription is already active for this league' },
          409,
        ),
      );
    });
    when('I click Subscribe on the paywall', async () => {
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });

  test('Manage billing redirects to the Stripe portal', ({
    given,
    when,
    then,
  }) => {
    given(
      'the league has an active subscription and a billing portal session',
      () => {
        server.use(
          leagueMetadata({ subscription_end_time: isoIn(30) }),
          postJson('/billing-portal-session', { data: { url: STRIPE_URL } }),
        );
        assignSpy = mockNavigation();
      },
    );
    when('I click Manage billing in the dialog', async () => {
      await renderRoute(
        <ManageSubscriptionDialog open onOpenChange={vi.fn()} />,
        { league },
      );
      await userEvent.click(
        await screen.findByRole('button', { name: /manage billing/i }),
      );
    });
    then('the browser is redirected to the Stripe URL', () => {
      expect(assignSpy).toHaveBeenCalledWith(STRIPE_URL);
    });
  });
});
