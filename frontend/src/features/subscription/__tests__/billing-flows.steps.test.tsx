import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
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
function mockNavigation(pathname = '/', search = '') {
  const assign = vi.fn();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { assign, search, pathname, href: `http://localhost${pathname}` },
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
      // Only the owner sees the Subscribe CTA (FE-025); the paywall reads
      // is_owner via getLeague.
      server.use(leagueMetadata({ is_owner: true }));
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then('the browser is redirected to the Stripe URL', () => {
      expect(assignSpy).toHaveBeenCalledWith(STRIPE_URL);
    });
  });

  test("The plan toggle shows each plan's price", ({ given, when, then }) => {
    given('a checkout session will be created', () => {
      assignSpy = mockNavigation();
    });
    when('I open the paywall as the owner', async () => {
      // Only the owner sees the plan toggle (FE-025).
      server.use(leagueMetadata({ is_owner: true }));
      await renderRoute(<SubscriptionRequired />, { league });
    });
    then(
      'I see the monthly price "$1.99/mo" and the yearly price "$8.99/yr"',
      async () => {
        expect(
          await screen.findByRole('radio', { name: /monthly/i }),
        ).toHaveTextContent('$1.99/mo');
        expect(
          screen.getByRole('radio', { name: /yearly/i }),
        ).toHaveTextContent('$8.99/yr');
      },
    );
  });

  test('Subscribing on the yearly plan sends the yearly plan', ({
    given,
    when,
    then,
  }) => {
    let capturedUrl = '';
    given('a checkout session will be created', () => {
      assignSpy = mockNavigation();
    });
    when('I pick the yearly plan and click Subscribe', async () => {
      // Only the owner sees the Subscribe CTA + plan toggle (FE-025).
      server.use(leagueMetadata({ is_owner: true }));
      // Capturing handler (registered last → takes precedence) records the URL so
      // we can assert the selected plan is sent through to the API.
      server.use(
        http.post('*/leagues/100/checkout-session', ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({ data: { url: STRIPE_URL } });
        }),
      );
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('radio', { name: /yearly/i }));
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then('the checkout request used the yearly plan', () => {
      expect(new URL(capturedUrl).searchParams.get('plan')).toBe('YEARLY');
    });
  });

  test('Subscribe sends the originating page as the return path', ({
    given,
    when,
    then,
  }) => {
    let capturedUrl = '';
    given('a checkout session will be created', () => {
      // Start checkout from the schedule-swap page so both the success and cancel
      // ("back") URLs should return the user here rather than /home (FE-022).
      assignSpy = mockNavigation('/schedule-swap');
    });
    when('I click Subscribe from the schedule-swap page', async () => {
      server.use(leagueMetadata({ is_owner: true }));
      server.use(
        http.post('*/leagues/100/checkout-session', ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({ data: { url: STRIPE_URL } });
        }),
      );
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then(
      'the checkout request sent the schedule-swap page as the return path',
      () => {
        expect(new URL(capturedUrl).searchParams.get('returnPath')).toBe(
          '/schedule-swap',
        );
        expect(assignSpy).toHaveBeenCalledWith(STRIPE_URL);
      },
    );
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
      // Only the owner sees the Subscribe CTA (FE-025); the paywall reads
      // is_owner via getLeague.
      server.use(leagueMetadata({ is_owner: true }));
      await renderRoute(<SubscriptionRequired />, { league });
      await userEvent.click(screen.getByRole('button', { name: /subscribe/i }));
    });
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });

  test('A server error on checkout shows an inline error', ({
    given,
    when,
    then,
  }) => {
    given('checkout fails with a server error', () => {
      // The backend recovers from a deleted Stripe customer; any other failure
      // returns a 502 with a JSON detail (BE-015), which must surface inline
      // rather than leaving the button silently idle.
      server.use(
        postJson(
          '/leagues/100/checkout-session',
          { detail: "Couldn't start checkout. Please try again." },
          502,
        ),
      );
    });
    when('I click Subscribe on the paywall', async () => {
      // Only the owner sees the Subscribe CTA (FE-025); the paywall reads
      // is_owner via getLeague.
      server.use(leagueMetadata({ is_owner: true }));
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
