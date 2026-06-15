import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import ScheduleSwap from '../schedule-swap';

import type { MatchupItem } from '@/components/api/types';
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
  'src/features/schedule_swap/__tests__/schedule-swap.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const NAMES: Record<string, string> = { T1: 'Alice', T2: 'Bob' };

function game(
  week: string,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: NAMES[aId],
    team_a_team_name: `Team ${NAMES[aId]}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: [],
    team_a_bench: [],
    team_a_primary_owner_id: `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: NAMES[bId],
    team_b_team_name: `Team ${NAMES[bId]}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: 'NONE',
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week,
    season: '2024',
  };
}

// Alice beats Bob both weeks → Alice 2-0, Bob 0-2.
const MATCHUPS: MatchupItem[] = [
  game('1', 'T1', 100, 'T2', 90),
  game('2', 'T1', 110, 'T2', 80),
];

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

async function openSimulator() {
  await renderRoute(
    <ScheduleSwap leagueId="100" platform="SLEEPER" season="2024" />,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('The matrix renders for a season with regular-season games', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season of regular-season matchups is available', () => {
      server.use(leagueQuery({ MATCHUPS }));
    });
    when('I open the schedule-swap simulator', openSimulator);
    then(/^I see the manager "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and(/^I see the actual record "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('A season without enough data shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the season has no regular-season matchups', () => {
      server.use(leagueQuery({ MATCHUPS: [] }));
    });
    when('I open the schedule-swap simulator', openSimulator);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the matchup data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the schedule-swap simulator', openSimulator);
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
        // Note: no MATCHUPS handler is registered. With MSW's
        // onUnhandledRequest: 'error', a schedule-swap data fetch would fail the
        // test — so this scenario also proves the gated component never fetches.
        server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
      },
    );
    when('I open the gated schedule-swap simulator', async () => {
      await renderRoute(
        <SubscriptionGuard
          featureFlag="premium_feature"
          featureLabel="Schedule-swap simulator"
        >
          <ScheduleSwap leagueId="100" platform="SLEEPER" season="2024" />
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and('the schedule-swap matrix is not rendered', () => {
      // No manager from the matrix renders, since the gated component never mounts.
      expect(screen.queryByText('Alice')).not.toBeInTheDocument();
    });
  });
});
