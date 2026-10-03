import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import {
  YAHOO_FANTASY_URL,
  YahooAttributionFooter,
} from '../yahoo-attribution-footer';

import type { Platform } from '@/lib/cookie-handler';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/yahoo-attribution-footer.feature',
);

const ATTRIBUTION = 'Fantasy data provided by Yahoo Fantasy';

defineFeature(feature, (test) => {
  let platform: Platform = 'YAHOO';
  let demo = false;

  async function renderFooter() {
    await renderRoute(<YahooAttributionFooter />, {
      league: { leagueId: '100', platform, seasons: ['2025'] },
      demo,
    });
  }

  function expectNoAttribution() {
    expect(screen.queryByText(ATTRIBUTION)).not.toBeInTheDocument();
    expect(screen.queryByAltText('Yahoo Fantasy')).not.toBeInTheDocument();
  }

  test('Yahoo league shows the attribution', ({ given, when, then }) => {
    given('I am viewing a Yahoo league', () => {
      platform = 'YAHOO';
      demo = false;
    });
    when('I render the attribution footer', renderFooter);
    then(
      'I see the Yahoo Fantasy logo and attribution text linking to Yahoo Fantasy',
      () => {
        const link = screen.getByRole('link', { name: /Yahoo Fantasy/ });
        expect(link).toHaveTextContent(ATTRIBUTION);
        expect(link).toHaveAttribute('href', YAHOO_FANTASY_URL);
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
        expect(screen.getByAltText('Yahoo Fantasy')).toBeInTheDocument();
      },
    );
  });

  test('ESPN league shows no attribution', ({ given, when, then }) => {
    given('I am viewing an ESPN league', () => {
      platform = 'ESPN';
      demo = false;
    });
    when('I render the attribution footer', renderFooter);
    then('I do not see the Yahoo attribution', expectNoAttribution);
  });

  test('Sleeper league shows no attribution', ({ given, when, then }) => {
    given('I am viewing a Sleeper league', () => {
      platform = 'SLEEPER';
      demo = false;
    });
    when('I render the attribution footer', renderFooter);
    then('I do not see the Yahoo attribution', expectNoAttribution);
  });

  test('Demo mode shows no attribution', ({ given, when, then }) => {
    given('I am viewing the demo league', () => {
      platform = 'YAHOO';
      demo = true;
    });
    when('I render the attribution footer', renderFooter);
    then('I do not see the Yahoo attribution', expectNoAttribution);
  });
});
