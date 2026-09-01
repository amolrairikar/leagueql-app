import { act, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { RefreshReminderBanner } from '../refresh-reminder-banner';

import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/refresh-reminder-banner.feature',
);

const REMINDER = /Refresh your ESPN league data/;

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
}

/** Flush the two getLeague fetches + their effects so the final state is settled. */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

defineFeature(feature, (test) => {
  async function renderBanner(platform: Platform, demo = false) {
    await renderRoute(<RefreshReminderBanner />, {
      league: { leagueId: '100', platform, seasons: ['2024'] },
      demo,
    });
  }

  test('Stale ESPN league shows the reminder to the owner', ({
    given,
    when,
    then,
  }) => {
    given('I am the owner of an ESPN league last refreshed 10 days ago', () => {
      server.use(
        leagueMetadata({ is_owner: true, last_refresh_at: daysAgo(10) }),
      );
    });
    when('I render the refresh reminder banner', () => renderBanner('ESPN'));
    then('I see the refresh reminder', async () => {
      expect(await screen.findByText(REMINDER)).toBeInTheDocument();
    });
  });

  test('Fresh ESPN league shows no reminder', ({ given, when, then }) => {
    given('I am the owner of an ESPN league last refreshed 1 day ago', () => {
      server.use(
        leagueMetadata({ is_owner: true, last_refresh_at: daysAgo(1) }),
      );
    });
    when('I render the refresh reminder banner', () => renderBanner('ESPN'));
    then('I do not see the refresh reminder', async () => {
      await flush();
      expect(screen.queryByText(REMINDER)).not.toBeInTheDocument();
    });
  });

  test('Never-refreshed ESPN league falls back to onboarded date', ({
    given,
    when,
    then,
  }) => {
    given(
      'I am the owner of an ESPN league never refreshed but onboarded 10 days ago',
      () => {
        server.use(
          leagueMetadata({
            is_owner: true,
            last_refresh_at: null,
            onboarded_at: daysAgo(10),
          }),
        );
      },
    );
    when('I render the refresh reminder banner', () => renderBanner('ESPN'));
    then('I see the refresh reminder', async () => {
      expect(await screen.findByText(REMINDER)).toBeInTheDocument();
    });
  });

  test('Recently onboarded ESPN league shows no reminder', ({
    given,
    when,
    then,
  }) => {
    given(
      'I am the owner of an ESPN league never refreshed but onboarded 1 day ago',
      () => {
        server.use(
          leagueMetadata({
            is_owner: true,
            last_refresh_at: null,
            onboarded_at: daysAgo(1),
          }),
        );
      },
    );
    when('I render the refresh reminder banner', () => renderBanner('ESPN'));
    then('I do not see the refresh reminder', async () => {
      await flush();
      expect(screen.queryByText(REMINDER)).not.toBeInTheDocument();
    });
  });

  test('Sleeper league never shows the reminder', ({ given, when, then }) => {
    given(
      'I am the owner of a Sleeper league last refreshed 10 days ago',
      () => {
        server.use(
          leagueMetadata({ is_owner: true, last_refresh_at: daysAgo(10) }),
        );
      },
    );
    when('I render the refresh reminder banner', () => renderBanner('SLEEPER'));
    then('I do not see the refresh reminder', async () => {
      await flush();
      expect(screen.queryByText(REMINDER)).not.toBeInTheDocument();
    });
  });

  test('A non-owner of a stale ESPN league sees no reminder', ({
    given,
    when,
    then,
  }) => {
    given(
      'I am a non-owner of an ESPN league last refreshed 10 days ago',
      () => {
        server.use(
          leagueMetadata({ is_owner: false, last_refresh_at: daysAgo(10) }),
        );
      },
    );
    when('I render the refresh reminder banner', () => renderBanner('ESPN'));
    then('I do not see the refresh reminder', async () => {
      await flush();
      expect(screen.queryByText(REMINDER)).not.toBeInTheDocument();
    });
  });

  test('Demo mode never shows the reminder', ({ given, when, then }) => {
    given('I am viewing a stale ESPN league in demo mode', () => {
      server.use(
        leagueMetadata({ is_owner: true, last_refresh_at: daysAgo(10) }),
      );
    });
    when('I render the refresh reminder banner', () =>
      renderBanner('ESPN', true),
    );
    then('I do not see the refresh reminder', async () => {
      await flush();
      expect(screen.queryByText(REMINDER)).not.toBeInTheDocument();
    });
  });
});
