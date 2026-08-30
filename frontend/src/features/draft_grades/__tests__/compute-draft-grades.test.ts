import { describe, expect, it } from 'vitest';

import type { DraftPickItem } from '../api-calls';
import {
  gradeDraftForTeam,
  isScorablePick,
  makeIsBustPick,
} from '../compute-draft-grades';

/** A draft pick carrying only the fields the grader reads (sensible defaults). */
function pick(overrides: Partial<DraftPickItem>): DraftPickItem {
  return {
    actual_position_rank: null,
    auto_draft_type_id: 0,
    bid_amount: 0,
    drafted_position_rank: 0,
    draft_rank_delta: null,
    is_auction: false,
    keeper: false,
    lineup_slot_id: 0,
    member_id: 'm',
    nominating_team_id: 0,
    overall_pick_number: 1,
    owner_username: 'user',
    pick_id: 1,
    player_id: 'p',
    player_name: 'Player',
    position: 'RB',
    reserved_for_keeper: false,
    round: 1,
    round_pick_number: 1,
    season: '2024',
    team_id: 't1',
    team_logo: '',
    team_name: 'Team',
    total_points: 100,
    trade_locked: false,
    vorp: null,
    ...overrides,
  };
}

describe('compute-draft-grades', () => {
  it('excludes kickers, defenses, and null-delta picks from scorable', () => {
    expect(isScorablePick(pick({ position: 'K', draft_rank_delta: 8 }))).toBe(
      false,
    );
    expect(
      isScorablePick(pick({ position: 'D/ST', draft_rank_delta: 8 })),
    ).toBe(false);
    expect(isScorablePick(pick({ draft_rank_delta: null }))).toBe(false);
    expect(isScorablePick(pick({ draft_rank_delta: 3 }))).toBe(true);
  });

  it('picks the highest-delta best and lowest-delta worst for a team', () => {
    const picks = [
      pick({ team_id: 't1', player_name: 'A', draft_rank_delta: 12 }),
      pick({ team_id: 't1', player_name: 'B', draft_rank_delta: -11 }),
      pick({ team_id: 't1', player_name: 'C', draft_rank_delta: 2 }),
      // Another team's pick must be ignored.
      pick({ team_id: 't2', player_name: 'Z', draft_rank_delta: 99 }),
    ];
    const grade = gradeDraftForTeam(picks, 't1');
    expect(grade.bestPick?.player_name).toBe('A');
    expect(grade.worstPick?.player_name).toBe('B');
  });

  it('counts steals (delta >= 5)', () => {
    const picks = [
      pick({ team_id: 't1', draft_rank_delta: 5 }),
      pick({ team_id: 't1', draft_rank_delta: 8 }),
      pick({ team_id: 't1', draft_rank_delta: 4 }),
    ];
    expect(gradeDraftForTeam(picks, 't1').steals).toBe(2);
  });

  it('flags a snake bust only when picked well before the last round', () => {
    // maxRound = 15; bust needs round <= 11 and <= 10, and delta <= -5.
    const picks = [
      pick({ team_id: 't1', round: 2, draft_rank_delta: -6 }), // bust
      pick({ team_id: 't1', round: 15, draft_rank_delta: -9 }), // too late → not a bust
      pick({ round: 15, draft_rank_delta: 0 }), // sets maxRound
    ];
    const isBust = makeIsBustPick(picks);
    expect(isBust(picks[0])).toBe(true);
    expect(isBust(picks[1])).toBe(false);
    expect(gradeDraftForTeam(picks, 't1').busts).toBe(1);
  });

  it('returns null best/worst when the team has no scorable picks', () => {
    const grade = gradeDraftForTeam(
      [pick({ team_id: 't1', position: 'K', draft_rank_delta: 9 })],
      't1',
    );
    expect(grade.bestPick).toBeNull();
    expect(grade.worstPick).toBeNull();
  });
});
