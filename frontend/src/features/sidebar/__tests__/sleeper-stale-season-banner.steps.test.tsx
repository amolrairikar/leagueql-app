import { act, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect, vi } from 'vitest';

import { SleeperStaleSeasonBanner } from '../sleeper-stale-season-banner';

import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/sleeper-stale-season-banner.feature',
);

const BANNER = /Not seeing your current season/;

/** Flush the getLeague fetch + effects so the final state is settled. */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

// Fake only `Date` (leaving setTimeout real for MSW/flush) so the current-fantasy
// season the hook derives from `new Date()` is deterministic. Month is 0-indexed:
// 7 = August (before the September flip), 8 = September.
function setDate(year: number, monthIndex: number, day: number) {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date(year, monthIndex, day, 12));
}

defineFeature(feature, (test) => {
  afterEach(() => {
    vi.useRealTimers();
  });

  async function renderBanner(opts: {
    platform?: Platform;
    seasons?: string[];
    demo?: boolean;
  }) {
    await renderRoute(<SleeperStaleSeasonBanner />, {
      league: {
        leagueId: '100',
        platform: opts.platform ?? 'SLEEPER',
        seasons: opts.seasons ?? [],
      },
      demo: opts.demo,
    });
  }

  test('Stale-season Sleeper league shows the banner to the owner', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and(
      'I am the owner of a Sleeper league whose latest onboarded season is 2025',
      () => {
        server.use(
          leagueMetadata({ is_owner: true, seasons: ['2024', '2025'] }),
        );
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2024', '2025'] }),
    );
    then(
      'I see the stale-season banner with a link to the landing page',
      async () => {
        expect(await screen.findByText(BANNER)).toBeInTheDocument();
        const link = screen.getByRole('link', { name: /landing page/i });
        expect(link).toHaveAttribute('href', '/');
      },
    );
  });

  test('Up-to-date Sleeper league shows no banner', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and(
      'I am the owner of a Sleeper league whose latest onboarded season is 2026',
      () => {
        server.use(leagueMetadata({ is_owner: true, seasons: ['2026'] }));
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2026'] }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });

  test('Before September the season has not yet flipped', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is August 2026', () => setDate(2026, 7, 15));
    and(
      'I am the owner of a Sleeper league whose latest onboarded season is 2025',
      () => {
        server.use(leagueMetadata({ is_owner: true, seasons: ['2025'] }));
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2025'] }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });

  test('In September the season flips and the banner appears', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is September 2026', () => setDate(2026, 8, 1));
    and(
      'I am the owner of a Sleeper league whose latest onboarded season is 2025',
      () => {
        server.use(leagueMetadata({ is_owner: true, seasons: ['2025'] }));
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2025'] }),
    );
    then(
      'I see the stale-season banner with a link to the landing page',
      async () => {
        expect(await screen.findByText(BANNER)).toBeInTheDocument();
        const link = screen.getByRole('link', { name: /landing page/i });
        expect(link).toHaveAttribute('href', '/');
      },
    );
  });

  test('A non-owner of a stale-season Sleeper league sees no banner', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and(
      'I am a non-owner of a Sleeper league whose latest onboarded season is 2025',
      () => {
        server.use(leagueMetadata({ is_owner: false, seasons: ['2025'] }));
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2025'] }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });

  test('ESPN league never shows the banner', ({ given, and, when, then }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and(
      'I am the owner of an ESPN league whose latest onboarded season is 2024',
      () => {
        server.use(leagueMetadata({ is_owner: true, seasons: ['2024'] }));
      },
    );
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'ESPN', seasons: ['2024'] }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });

  test('Demo mode never shows the banner', ({ given, and, when, then }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and('I am viewing a stale-season Sleeper league in demo mode', () => {
      server.use(leagueMetadata({ is_owner: true, seasons: ['2025'] }));
    });
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: ['2025'], demo: true }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });

  test('A league with no onboarded seasons shows no banner', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the date is September 2026', () => setDate(2026, 8, 15));
    and('I am the owner of a Sleeper league with no onboarded seasons', () => {
      server.use(leagueMetadata({ is_owner: true, seasons: [] }));
    });
    when('I render the stale-season banner', () =>
      renderBanner({ platform: 'SLEEPER', seasons: [] }),
    );
    then('I do not see the stale-season banner', async () => {
      await flush();
      expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    });
  });
});
