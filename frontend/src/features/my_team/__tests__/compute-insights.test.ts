import { describe, expect, it } from 'vitest';

import { computeInsights, heroVerdict, ordinal } from '../compute-insights';

import { baseMetrics, draftPick } from './factories';

describe('compute-insights', () => {
  it('formats ordinals correctly', () => {
    expect(ordinal(1)).toBe('1st');
    expect(ordinal(2)).toBe('2nd');
    expect(ordinal(3)).toBe('3rd');
    expect(ordinal(4)).toBe('4th');
    expect(ordinal(11)).toBe('11th');
    expect(ordinal(22)).toBe('22nd');
  });

  it('fires the unlucky rule with a templated sentence and metric', () => {
    const m = baseMetrics({
      luck: -1.3,
      pfRank: 2,
      seed: 4,
      expectedWins: 8.3,
      wins: 7,
    });
    const insights = computeInsights(m);
    const unlucky = insights.find((i) => i.id === 'unlucky');
    expect(unlucky).toBeDefined();
    expect(unlucky!.sentiment).toBe('warn');
    expect(unlucky!.sentence).toContain('2nd-most points');
    expect(unlucky!.sentence).toContain('4th seed');
    expect(unlucky!.metric.value).toBe('-1.3');
  });

  it('fires the bench-leak rule below 94% efficiency', () => {
    const leak = computeInsights(
      baseMetrics({ efficiency: 0.91, pointsLeft: 118 }),
    );
    expect(leak.some((i) => i.id === 'bench-leak')).toBe(true);
    const sharp = computeInsights(baseMetrics({ efficiency: 0.98 }));
    expect(sharp.some((i) => i.id === 'bench-leak')).toBe(false);
    expect(sharp.some((i) => i.id === 'lineup-sharp')).toBe(true);
  });

  it('fires a draft steal from the best pick', () => {
    const m = baseMetrics({
      draft: {
        bestPick: draftPick({
          player_name: 'Bijan',
          round: 3,
          position: 'RB',
          actual_position_rank: 6,
          draft_rank_delta: 12,
        }),
        worstPick: null,
        steals: 1,
        busts: 0,
        scorablePicks: [],
      },
    });
    const steal = computeInsights(m).find((i) => i.id === 'draft-steal');
    expect(steal?.headline).toContain('Bijan');
    expect(steal?.metric.value).toBe('+12');
  });

  it('does not fire trade insights without trades (e.g. ESPN)', () => {
    const espn = baseMetrics({
      platform: 'ESPN',
      trades: { best: null, worst: null, tradeCount: 0, waiverCount: 0 },
    });
    const insights = computeInsights(espn);
    expect(insights.some((i) => i.id === 'best-trade')).toBe(false);
    expect(insights.some((i) => i.id === 'trade-regret')).toBe(false);
  });

  it('ranks the highest-severity insight first', () => {
    const m = baseMetrics({
      luck: -2, // strong unlucky (base 60 + magnitude)
      pfRank: 1,
      seed: 5,
      efficiency: 0.99, // lineup-sharp (base ~25) — lower priority
    });
    const insights = computeInsights(m);
    expect(insights[0].id).toBe('unlucky');
  });

  it('caps the number of insights', () => {
    const m = baseMetrics({ luck: -2, efficiency: 0.9, pfRank: 1 });
    expect(computeInsights(m).length).toBeLessThanOrEqual(6);
  });

  it('generates a hero verdict from the top theme', () => {
    const m = baseMetrics({ luck: -1.5, pfRank: 2, seed: 5 });
    const insights = computeInsights(m);
    const verdict = heroVerdict(m, insights);
    expect(verdict.toLowerCase()).toContain('standings are hiding');
  });
});
