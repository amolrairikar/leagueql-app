import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { DraftValueScatter } from '../draft-recap';

import type { DraftPickItem } from '@/features/draft_grades/api-calls';
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
  'src/features/draft_recap/__tests__/draft-scatter.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

/** Minimal draft pick; only the fields the scatter reads are meaningful. */
function pick(overrides: Partial<DraftPickItem>): DraftPickItem {
  return {
    actual_position_rank: null,
    auto_draft_type_id: 0,
    bid_amount: 0,
    drafted_position_rank: 1,
    draft_rank_delta: null,
    is_auction: false,
    keeper: false,
    lineup_slot_id: 0,
    member_id: 'm',
    nominating_team_id: 0,
    overall_pick_number: 1,
    owner_username: 'Alice',
    pick_id: 1,
    player_id: 'p1',
    player_name: 'Player',
    position: 'QB',
    reserved_for_keeper: false,
    round: 1,
    round_pick_number: 1,
    season: '2024',
    team_id: '1',
    team_logo: '',
    team_name: 'Team Alice',
    total_points: 100,
    trade_locked: false,
    vorp: null,
    ...overrides,
  };
}

const DRAFT: DraftPickItem[] = [
  pick({ overall_pick_number: 1, position: 'QB', total_points: 300 }),
  pick({ overall_pick_number: 2, position: 'RB', total_points: 250 }),
  pick({ overall_pick_number: 3, position: 'WR', total_points: 200 }),
];

// Every pick lacks a scoring row, so nothing is plottable.
const DRAFT_UNSCORED: DraftPickItem[] = [
  pick({ overall_pick_number: 1, position: 'QB', total_points: null }),
  pick({ overall_pick_number: 2, position: 'DEF', total_points: null }),
];

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

async function openScatter() {
  await renderRoute(
    <DraftValueScatter
      leagueId="100"
      platform="SLEEPER"
      season="2024"
      auction={false}
    />,
    { league },
  );
}

defineFeature(feature, (test) => {
  test('The scatter renders a legend of the positions present', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a season of scored draft picks is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft value scatter', openScatter);
    then(/^I see the position "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
    and(/^I see the position "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
  });

  test('Filtering to a position narrows the plot to that position', ({
    given,
    when,
    and,
    then,
  }) => {
    const user = userEvent.setup();
    given('a season of scored draft picks is available', () => {
      server.use(leagueQuery({ DRAFT }));
    });
    when('I open the draft value scatter', openScatter);
    and(/^I filter to the position "(.*)"$/, async (label) => {
      // Wait for the chart before opening the position dropdown.
      expect((await screen.findAllByText('QB')).length).toBeGreaterThan(0);
      await user.click(await screen.findByRole('combobox'));
      await user.click(await screen.findByRole('option', { name: label }));
    });
    then(/^I see the position "(.*)"$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
    and(/^I do not see the position "(.*)"$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });

  test('A season with no scored picks shows an empty state', ({
    given,
    when,
    then,
  }) => {
    given('the season has draft picks but none are scored', () => {
      server.use(leagueQuery({ DRAFT: DRAFT_UNSCORED }));
    });
    when('I open the draft value scatter', openScatter);
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed load surfaces an inline message', ({ given, when, then }) => {
    given('the draft data fails to load', () => {
      server.use(leagueQueryError(500));
    });
    when('I open the draft value scatter', openScatter);
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
        // No DRAFT handler is registered. With MSW's onUnhandledRequest: 'error',
        // a data fetch would fail the test — so this also proves the gated
        // component never fetches while locked.
        server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
      },
    );
    when('I open the gated draft value scatter', async () => {
      await renderRoute(
        <SubscriptionGuard
          featureFlag="premium_feature"
          featureLabel="Draft value"
        >
          <DraftValueScatter
            leagueId="100"
            platform="SLEEPER"
            season="2024"
            auction={false}
          />
        </SubscriptionGuard>,
        { league },
      );
    });
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and('the draft value scatter is not rendered', () => {
      // The position filter never mounts, so its dropdown is absent.
      expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    });
  });
});
