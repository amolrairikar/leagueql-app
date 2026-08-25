import { describe, expect, it } from 'vitest';

import { isUnplayedMatchup } from '../matchups';

import type { MatchupItem } from '@/components/api/types';

function matchup(team_a_score: number, team_b_score: number): MatchupItem {
  return { team_a_score, team_b_score } as MatchupItem;
}

describe('isUnplayedMatchup', () => {
  it('treats a 0-0 matchup as unplayed', () => {
    expect(isUnplayedMatchup(matchup(0, 0))).toBe(true);
  });

  it('keeps a played game where one team scored 0', () => {
    expect(isUnplayedMatchup(matchup(0, 88.5))).toBe(false);
    expect(isUnplayedMatchup(matchup(101.2, 0))).toBe(false);
  });

  it('keeps a normal played game', () => {
    expect(isUnplayedMatchup(matchup(130, 120))).toBe(false);
  });
});
