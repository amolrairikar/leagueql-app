import { describe, expect, it } from 'vitest';

import {
  computeStartSitReport,
  deriveRequiredSlots,
  optimalLineup,
} from '../compute-lineup-efficiency';

import type { PlayerStat } from '@/components/api/types';

let nextId = 1;

/** Build a PlayerStat; `slot` (when given) is the started lineup slot. */
function player(
  position: string,
  pointsScored: number,
  opts: { slot?: string; name?: string; id?: number } = {},
): PlayerStat {
  const id = opts.id ?? nextId++;
  return {
    player_id: id,
    full_name: opts.name ?? `${position} ${id}`,
    points_scored: pointsScored,
    position,
    ...(opts.slot ? { fantasy_position: opts.slot } : {}),
  };
}

describe('optimalLineup', () => {
  it('finds the true optimum where a greedy slot-fill would not (non-laminar slots)', () => {
    // Two overlapping flex slots: RB/WR = {RB,WR}, WR/TE = {WR,TE}. A single WR
    // stud is eligible for both. A greedy that hands the WR/TE slot the stud
    // (displacing the TE) scores 11; the optimum puts the stud in RB/WR and keeps
    // the TE, scoring 19.
    const starters = [
      player('RB', 1, { slot: 'RB/WR', name: 'RB Guy' }),
      player('TE', 9, { slot: 'WR/TE', name: 'TE Guy' }),
    ];
    const bench = [player('WR', 10, { name: 'WR Stud' })];

    const { optimalPoints, assignment } = optimalLineup(starters, bench);

    expect(optimalPoints).toBeCloseTo(19, 5);
    // The WR stud takes the RB/WR slot (index 0), the TE keeps WR/TE (index 1).
    expect(assignment.get(0)?.full_name).toBe('WR Stud');
    expect(assignment.get(1)?.full_name).toBe('TE Guy');
  });

  it('cannot beat an already-legal lineup when the bench is empty', () => {
    const starters = [
      player('QB', 20, { slot: 'QB' }),
      player('RB', 10, { slot: 'RB' }),
    ];
    const { optimalPoints } = optimalLineup(starters, []);
    expect(optimalPoints).toBeCloseTo(30, 5);
  });

  it('is deterministic across runs when bench players tie', () => {
    const starters = [player('RB', 5, { slot: 'RB' })];
    const bench = [player('RB', 12, { id: 7 }), player('RB', 12, { id: 3 })];
    const a = optimalLineup(starters, bench).optimalPoints;
    const b = optimalLineup(starters, bench).optimalPoints;
    expect(a).toBeCloseTo(12, 5);
    expect(a).toBe(b);
  });
});

describe('deriveRequiredSlots', () => {
  it('tallies one slot per starter from fantasy_position', () => {
    const starters = [
      player('QB', 1, { slot: 'QB' }),
      player('RB', 1, { slot: 'RB' }),
      player('RB', 1, { slot: 'RB' }),
      player('WR', 1, { slot: 'FLEX' }),
    ];
    expect(deriveRequiredSlots(starters)).toEqual(['QB', 'RB', 'RB', 'FLEX']);
  });
});

describe('computeStartSitReport', () => {
  it('reports the slot-by-slot delta and totals for the greedy-trap lineup', () => {
    const starters = [
      player('RB', 1, { slot: 'RB/WR', name: 'RB Guy' }),
      player('TE', 9, { slot: 'WR/TE', name: 'TE Guy' }),
    ];
    const bench = [player('WR', 10, { name: 'WR Stud' })];

    const report = computeStartSitReport(starters, bench);

    expect(report.hasBenchData).toBe(true);
    expect(report.actualPoints).toBeCloseTo(10, 5);
    expect(report.optimalPoints).toBeCloseTo(19, 5);
    expect(report.pointsLeft).toBeCloseTo(9, 5);
    expect(report.efficiencyPct).toBeCloseTo(10 / 19, 5);

    const changed = report.rows.filter((r) => r.delta > 0);
    expect(changed).toHaveLength(1);
    expect(changed[0].slot).toBe('RB/WR');
    expect(changed[0].started?.name).toBe('RB Guy');
    expect(changed[0].optimal?.name).toBe('WR Stud');
    expect(changed[0].delta).toBeCloseTo(9, 5);

    // Per-row deltas always sum to the points left on the bench.
    const sum = report.rows.reduce((s, r) => s + r.delta, 0);
    expect(sum).toBeCloseTo(report.pointsLeft, 5);
  });

  it('flags no bench data and 100% efficiency for an empty bench', () => {
    const starters = [
      player('QB', 20, { slot: 'QB' }),
      player('RB', 10, { slot: 'RB' }),
    ];
    const report = computeStartSitReport(starters, []);
    expect(report.hasBenchData).toBe(false);
    expect(report.efficiencyPct).toBe(1);
    expect(report.pointsLeft).toBe(0);
    expect(report.rows.every((r) => r.delta === 0)).toBe(true);
  });

  it('swaps in a higher-scoring bench player for a plain slot', () => {
    const starters = [player('RB', 5, { slot: 'RB', name: 'Started RB' })];
    const bench = [player('RB', 12, { name: 'Bench RB' })];
    const report = computeStartSitReport(starters, bench);
    expect(report.pointsLeft).toBeCloseTo(7, 5);
    expect(report.rows[0].started?.name).toBe('Started RB');
    expect(report.rows[0].optimal?.name).toBe('Bench RB');
  });

  it('lets a FLEX slot pull in an eligible bench WR', () => {
    const starters = [player('RB', 5, { slot: 'FLEX' })];
    const bench = [player('WR', 12)];
    expect(computeStartSitReport(starters, bench).pointsLeft).toBeCloseTo(7, 5);
  });

  it('normalizes D/ST and DEF so either fills the defense slot', () => {
    const starters = [player('D/ST', 3, { slot: 'D/ST', name: 'ESPN DEF' })];
    const bench = [player('DEF', 8, { name: 'Sleeper DEF' })];
    const report = computeStartSitReport(starters, bench);
    expect(report.pointsLeft).toBeCloseTo(5, 5);
    expect(report.rows[0].optimal?.name).toBe('Sleeper DEF');
  });

  it('ignores a bench player ineligible for any open slot', () => {
    const starters = [player('K', 5, { slot: 'K' })];
    const bench = [player('QB', 30)];
    expect(computeStartSitReport(starters, bench).pointsLeft).toBe(0);
  });

  it('reports a perfect lineup as 100% with no changed rows', () => {
    const starters = [
      player('QB', 20, { slot: 'QB' }),
      player('RB', 10, { slot: 'RB' }),
    ];
    const bench = [player('RB', 2)];
    const report = computeStartSitReport(starters, bench);
    expect(report.efficiencyPct).toBe(1);
    expect(report.pointsLeft).toBe(0);
    expect(report.rows.some((r) => r.delta > 0)).toBe(false);
  });
});
