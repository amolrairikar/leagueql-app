import { act, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { EspnReauthBanner } from '../espn-reauth-banner';

import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/espn-reauth-banner.feature',
);

const MESSAGE = /ESPN rejected your saved cookies/;

/** Flush the getLeague fetch + its effect so the final state is settled. */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function rejectedCookies(isOwner = true) {
  return leagueMetadata({
    is_owner: isOwner,
    auto_refresh_enabled: true,
    // The backend only reports re-auth to the owner; a non-owner never gets it.
    espn_reauth_required: isOwner,
    espn_credentials_failed_at: isOwner ? '2026-10-01T09:00:00+00:00' : null,
  });
}

defineFeature(feature, (test) => {
  async function renderBanner(platform: Platform, demo = false) {
    await renderRoute(<EspnReauthBanner />, {
      league: { leagueId: '100', platform, seasons: ['2024'] },
      demo,
    });
  }

  async function expectNoBanner() {
    await flush();
    expect(screen.queryByText(MESSAGE)).not.toBeInTheDocument();
  }

  test('The owner sees the banner when their saved cookies were rejected', ({
    given,
    when,
    then,
  }) => {
    given('I own an ESPN league whose saved cookies ESPN rejected', () => {
      server.use(rejectedCookies());
    });
    when('I render the ESPN re-auth banner', () => renderBanner('ESPN'));
    then('I see the re-auth banner with no dismiss control', async () => {
      expect(await screen.findByText(MESSAGE)).toBeInTheDocument();
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Update ESPN Cookies',
      );
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  test('Healthy cookies show no banner', ({ given, when, then }) => {
    given(
      'I own an auto-refreshed ESPN league whose saved cookies still work',
      () => {
        server.use(
          leagueMetadata({
            is_owner: true,
            auto_refresh_enabled: true,
            espn_reauth_required: false,
          }),
        );
      },
    );
    when('I render the ESPN re-auth banner', () => renderBanner('ESPN'));
    then('I do not see the re-auth banner', expectNoBanner);
  });

  test('A non-owner sees no banner', ({ given, when, then }) => {
    given('I am a non-owner of an ESPN league', () => {
      server.use(rejectedCookies(false));
    });
    when('I render the ESPN re-auth banner', () => renderBanner('ESPN'));
    then('I do not see the re-auth banner', expectNoBanner);
  });

  test('A Sleeper league never shows the banner', ({ given, when, then }) => {
    given(
      'I own a Sleeper league whose metadata reports re-auth required',
      () => {
        server.use(rejectedCookies());
      },
    );
    when('I render the ESPN re-auth banner', () => renderBanner('SLEEPER'));
    then('I do not see the re-auth banner', expectNoBanner);
  });

  test('Demo mode never shows the banner', ({ given, when, then }) => {
    given(
      'I am viewing an ESPN league with rejected cookies in demo mode',
      () => {
        server.use(rejectedCookies());
      },
    );
    when('I render the ESPN re-auth banner', () => renderBanner('ESPN', true));
    then('I do not see the re-auth banner', expectNoBanner);
  });
});
