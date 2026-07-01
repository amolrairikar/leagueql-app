import { describe, expect, it } from 'vitest';

import { computeDraftScatter, UNKNOWN_PLAYER } from '../compute-draft-scatter';

import type { DraftPickItem } from '@/features/draft_grades/api-calls';

/** Minimal draft pick; only the fields the scatter transform reads matter. */
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
    player_name: 'Pat Quarterback',
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

describe('computeDraftScatter', () => {
  it('builds one dot per scored pick with the tooltip fields', () => {
    const { points } = computeDraftScatter([
      pick({
        overall_pick_number: 5,
        total_points: 250.4,
        player_name: 'Pat Quarterback',
        owner_username: 'Alice',
        position: 'QB',
      }),
    ]);

    expect(points).toEqual([
      {
        pick: 5,
        points: 250.4,
        player: 'Pat Quarterback',
        manager: 'Alice',
        position: 'QB',
      },
    ]);
  });

  it('omits picks with no season points rather than plotting them at zero', () => {
    const { points } = computeDraftScatter([
      pick({ player_name: 'Scored', total_points: 120 }),
      pick({
        player_name: 'Unscored DST',
        position: 'DEF',
        total_points: null,
      }),
    ]);

    expect(points.map((p) => p.player)).toEqual(['Scored']);
  });

  it('skips picks whose draft position or points are not finite', () => {
    const { points } = computeDraftScatter([
      pick({ overall_pick_number: Number.NaN, total_points: 100 }),
      pick({ total_points: Number.POSITIVE_INFINITY }),
      pick({ overall_pick_number: 3, total_points: 80, player_name: 'Ok' }),
    ]);

    expect(points.map((p) => p.player)).toEqual(['Ok']);
  });

  it('falls back to a placeholder for a pick with no player name', () => {
    const { points } = computeDraftScatter([pick({ player_name: null })]);

    expect(points[0].player).toBe(UNKNOWN_PLAYER);
  });

  it('lists distinct present positions in fantasy display order', () => {
    const { positions } = computeDraftScatter([
      pick({ position: 'K', total_points: 50 }),
      pick({ position: 'QB', total_points: 200 }),
      pick({ position: 'RB', total_points: 150 }),
      pick({ position: 'QB', total_points: 180 }),
    ]);

    // FANTASY_POSITION_ORDER: QB (0) < RB (3) < K (10); no duplicate QB.
    expect(positions).toEqual(['QB', 'RB', 'K']);
  });

  it('orders positions QB RB WR TE D/ST K with Sleeper DEF in the D/ST slot', () => {
    const { positions } = computeDraftScatter([
      pick({ position: 'K', total_points: 50 }),
      pick({ position: 'DEF', total_points: 90 }),
      pick({ position: 'TE', total_points: 120 }),
      pick({ position: 'WR', total_points: 160 }),
      pick({ position: 'RB', total_points: 150 }),
      pick({ position: 'QB', total_points: 200 }),
    ]);

    expect(positions).toEqual(['QB', 'RB', 'WR', 'TE', 'DEF', 'K']);
  });

  it('excludes positions of omitted (unscored) picks from the position list', () => {
    const { positions } = computeDraftScatter([
      pick({ position: 'QB', total_points: 200 }),
      pick({ position: 'DEF', total_points: null }),
    ]);

    expect(positions).toEqual(['QB']);
  });
});
