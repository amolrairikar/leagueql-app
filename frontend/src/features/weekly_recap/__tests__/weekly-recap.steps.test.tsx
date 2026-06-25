import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect, vi } from 'vitest';

import WeeklyRecap from '../weekly-recap';

import { SubscriptionGuard } from '@/features/subscription/subscription-guard';
import { setFlagsForTesting } from '@/lib/feature-flags';
import {
  leagueMetadata,
  leagueQuery,
  leagueQueryError,
  server,
} from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/weekly_recap/__tests__/weekly-recap.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

// The recap component resolves the active week from the season's matchups, so a
// single week-1 matchup is enough to drive the recap fetch for WEEK#01.
const MATCHUPS = [{ week: '1', season: '2024' }];

const RECAP = {
  headline: 'Week 1: Fireworks and Faceplants',
  body: 'Alice torched the scoreboard.\n\nBob, meanwhile, faceplanted.',
  generated_at: '2024-09-10T13:45:00+00:00',
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

async function openRecap() {
  await renderRoute(
    <WeeklyRecap
      leagueId="100"
      platform="SLEEPER"
      season="2024"
      selectedWeek={null}
    />,
    { league },
  );
}

defineFeature(feature, (test) => {
  const realClipboard = navigator.clipboard;
  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: realClipboard,
      configurable: true,
    });
  });

  test('The recap renders for a week with a cached recap', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a cached recap is available for the season', () => {
      server.use(leagueQuery({ MATCHUPS, MATCHUP_RECAP: [RECAP] }));
    });
    when('I open the weekly recap', openRecap);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('Copying a recap writes it to the clipboard and shows a check mark', ({
    given,
    when,
    then,
    and,
  }) => {
    const writeText = vi.fn().mockResolvedValue(undefined);

    given('a cached recap is available for the season', () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText },
        configurable: true,
      });
      server.use(leagueQuery({ MATCHUPS, MATCHUP_RECAP: [RECAP] }));
    });
    when('I open the weekly recap', openRecap);
    and('I click the copy recap button', async () => {
      const button = await screen.findByRole('button', { name: 'Copy recap' });
      await userEvent.click(button);
    });
    then('the recap headline and body are written to the clipboard', () => {
      expect(writeText).toHaveBeenCalledWith(
        `${RECAP.headline}\n\n${RECAP.body}`,
      );
    });
    and('the copy button shows it has copied', async () => {
      expect(
        await screen.findByRole('button', { name: 'Recap copied' }),
      ).toBeInTheDocument();
    });
  });

  test('A week with no cached recap shows the generating message', ({
    given,
    when,
    then,
  }) => {
    given('the week has no cached recap', () => {
      // MATCHUPS resolves the week; MATCHUP_RECAP is unmapped → 404 → empty state.
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the weekly recap', openRecap);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the recap data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the weekly recap', openRecap);
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
        // No query handler registered. With MSW's onUnhandledRequest: 'error', a
        // data fetch would fail the test — so this also proves the gated component
        // never fetches while locked.
        server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
      },
    );
    when('I open the gated weekly recap', async () => {
      await renderRoute(
        <SubscriptionGuard
          featureFlag="premium_feature"
          featureLabel="Weekly matchup recap"
        >
          <WeeklyRecap
            leagueId="100"
            platform="SLEEPER"
            season="2024"
            selectedWeek={null}
          />
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and('the recap is not rendered', () => {
      expect(
        screen.queryByText('Week 1: Fireworks and Faceplants'),
      ).not.toBeInTheDocument();
    });
  });
});
