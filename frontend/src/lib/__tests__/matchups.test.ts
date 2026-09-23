import { describe, expect, it } from 'vitest';

import { buildTeamColorMap, isUnplayedMatchup } from '../matchups';

import type { MatchupItem } from '@/components/api/types';
import { avatarColor } from '@/lib/color-constants';

function matchup(team_a_score: number, team_b_score: number): MatchupItem {
  return { team_a_score, team_b_score } as MatchupItem;
}

function teams(
  team_a_id: string,
  team_a_display_name: string,
  team_b_id: string,
  team_b_display_name: string,
): MatchupItem {
  return {
    team_a_id,
    team_a_display_name,
    team_b_id,
    team_b_display_name,
  } as MatchupItem;
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

describe('buildTeamColorMap', () => {
  it('assigns colors by display-name order regardless of matchup order', () => {
    const map = buildTeamColorMap([
      teams('zid', 'Zed', 'aid', 'Alice'),
      teams('mid', 'Mia', 'aid', 'Alice'),
    ]);
    // Sorted by display name: Alice (aid), Mia (mid), Zed (zid).
    expect(map.get('aid')).toBe(avatarColor(0));
    expect(map.get('mid')).toBe(avatarColor(1));
    expect(map.get('zid')).toBe(avatarColor(2));
  });

  it('is empty for no matchups', () => {
    expect(buildTeamColorMap([]).size).toBe(0);
  });

  it('tolerates a missing display name (treated as empty, sorts first)', () => {
    const m = teams('aid', 'Alice', 'bid', 'Bob');
    delete (m as { team_b_display_name?: string }).team_b_display_name;
    const map = buildTeamColorMap([m]);
    expect(map.get('bid')).toBe(avatarColor(0));
    expect(map.get('aid')).toBe(avatarColor(1));
  });
});
