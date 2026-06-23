import { fireEvent, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import { LineupEfficiencyChip } from '../lineup-efficiency-chip';

import type { PlayerStat } from '@/components/api/types';
import type { BoxScoreSide } from '@/components/box-score-card';
import { setFlagsForTesting } from '@/lib/feature-flags';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/lineup_efficiency/__tests__/lineup-efficiency-chip.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

function side(starters: PlayerStat[], bench: PlayerStat[]): BoxScoreSide {
  return {
    teamLogo: null,
    teamName: 'Team Alice',
    ownerUsername: 'Alice',
    color: '#000',
    score: starters.reduce((s, p) => s + p.points_scored, 0),
    starters,
    bench,
    isWinner: false,
  };
}

// A lineup where benching the WR stud cost points: actual 10, optimal 19 → 53%.
const MISTAKE_SIDE = side(
  [
    {
      player_id: 1,
      full_name: 'RB Guy',
      points_scored: 1,
      position: 'RB',
      fantasy_position: 'RB/WR',
    },
    {
      player_id: 2,
      full_name: 'TE Guy',
      points_scored: 9,
      position: 'TE',
      fantasy_position: 'WR/TE',
    },
  ],
  [{ player_id: 3, full_name: 'WR Stud', points_scored: 10, position: 'WR' }],
);

const PERFECT_SIDE = side(
  [
    {
      player_id: 1,
      full_name: 'QB Guy',
      points_scored: 20,
      position: 'QB',
      fantasy_position: 'QB',
    },
    {
      player_id: 2,
      full_name: 'RB Guy',
      points_scored: 10,
      position: 'RB',
      fantasy_position: 'RB',
    },
  ],
  [{ player_id: 3, full_name: 'Bench RB', points_scored: 2, position: 'RB' }],
);

// Empty bench (e.g. ESPN seasons before 2018) — nothing to optimize against.
const NO_BENCH_SIDE = side(
  [
    {
      player_id: 1,
      full_name: 'QB Guy',
      points_scored: 20,
      position: 'QB',
      fantasy_position: 'QB',
    },
  ],
  [],
);

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

function openReport() {
  fireEvent.click(screen.getByRole('button'));
}

defineFeature(feature, (test) => {
  const renderChip = (chipSide: BoxScoreSide, demo = false) =>
    renderRoute(<LineupEfficiencyChip side={chipSide} week="7" />, {
      ...(demo ? { demo: true } : { league }),
    });

  test('An active subscription shows the chip and start/sit report', ({
    given,
    when,
    then,
  }) => {
    given(
      'the premium_feature flag is on and the league subscription is active',
      () => {
        setFlagsForTesting({ billing: true, premium_feature: true });
        server.use(leagueMetadata({ subscription_end_time: isoIn(30) }));
      },
    );
    when(
      'I view the box score chip for a manager who left points on the bench',
      () => renderChip(MISTAKE_SIDE),
    );
    then(/^the chip shows "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('I open the start/sit report', openReport);
    then(
      /^I see the benched player "(.*)" listed as the optimal choice$/,
      async (name) => {
        expect(await screen.findByText(new RegExp(name))).toBeInTheDocument();
      },
    );
  });

  test('An expired subscription locks the chip behind the paywall', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      'the premium_feature flag is on and the league subscription has expired',
      () => {
        setFlagsForTesting({ billing: true, premium_feature: true });
        server.use(leagueMetadata({ subscription_end_time: isoIn(-1) }));
      },
    );
    when(
      'I view the box score chip for a manager who left points on the bench',
      () => renderChip(MISTAKE_SIDE),
    );
    then(
      /^the chip shows "(.*)" without an efficiency percentage$/,
      async (text) => {
        expect(await screen.findByText(text)).toBeInTheDocument();
        expect(screen.queryByText(/% efficient/)).not.toBeInTheDocument();
      },
    );
    when('I open the start/sit report', openReport);
    then(/^I see the paywall heading "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    and(/^the benched player "(.*)" is not shown$/, (name) => {
      expect(screen.queryByText(new RegExp(name))).not.toBeInTheDocument();
    });
  });

  test('Without the premium flag the chip is free', ({ given, when, then }) => {
    given('the premium_feature flag is off', () => {
      setFlagsForTesting({ billing: true, premium_feature: false });
      server.use(leagueMetadata({ subscription_end_time: null }));
    });
    when(
      'I view the box score chip for a manager who left points on the bench',
      () => renderChip(MISTAKE_SIDE),
    );
    then(/^the chip shows "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('I open the start/sit report', openReport);
    then(
      /^I see the benched player "(.*)" listed as the optimal choice$/,
      async (name) => {
        expect(await screen.findByText(new RegExp(name))).toBeInTheDocument();
      },
    );
  });

  test('With billing disabled no chip is shown', ({ given, when, then }) => {
    given('the billing flag is off', () => {
      setFlagsForTesting({ billing: false });
    });
    when(
      'I view the box score chip for a manager who left points on the bench',
      () => renderRoute(<LineupEfficiencyChip side={MISTAKE_SIDE} />),
    );
    then('no chip is rendered', () => {
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  test('Without bench data no chip is shown', ({ given, when, then }) => {
    given(
      'the premium_feature flag is on and the league subscription is active',
      () => {
        setFlagsForTesting({ billing: true, premium_feature: true });
      },
    );
    when('I view the box score chip for a season with no bench data', () =>
      renderRoute(<LineupEfficiencyChip side={NO_BENCH_SIDE} />),
    );
    then('no chip is rendered', () => {
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  test('Demo mode unlocks the chip with a premium hint', ({
    given,
    when,
    then,
  }) => {
    given('the app is in demo mode', () => {
      setFlagsForTesting({ billing: true, premium_feature: true });
    });
    when(
      'I view the box score chip for a manager who left points on the bench',
      () => renderChip(MISTAKE_SIDE, true),
    );
    then(/^the chip shows "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('I open the start/sit report', openReport);
    then(/^I see the "(.*)" hint$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A perfect lineup shows full efficiency', ({ given, when, then }) => {
    given(
      'the premium_feature flag is on and the league subscription is active',
      () => {
        setFlagsForTesting({ billing: true, premium_feature: true });
        server.use(leagueMetadata({ subscription_end_time: isoIn(30) }));
      },
    );
    when('I view the box score chip for a manager with a perfect lineup', () =>
      renderChip(PERFECT_SIDE),
    );
    then(/^the chip shows "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('I open the start/sit report', openReport);
    then(/^I see "(.*)" in the report$/, async (text) => {
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
    });
  });
});
