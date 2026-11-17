import { describe, expect, it } from 'vitest';

import { marginSummary } from '../clinch-format';
import { type TieMargin } from '../compute-projection';

const team = { teamName: 'Wolves', ownerUsername: 'wolf-owner' };

const margin = (name: string, gap: number): TieMargin =>
  ({
    rival: { teamId: name, teamName: name, ownerUsername: `${name}-owner` },
    gap,
  }) as unknown as TieMargin;

describe('marginSummary', () => {
  it('reports the tightest lead when ahead of every rival', () => {
    expect(
      marginSummary(team, [
        margin('A', 171),
        margin('B', 49.4),
        margin('C', 260),
      ]),
    ).toBe('Wolves leads by 49');
  });

  it('names the rival when trailing one', () => {
    expect(marginSummary(team, [margin('A', 30), margin('Hawks', -15.2)])).toBe(
      'Wolves trails Hawks by 15',
    );
  });

  it('falls back to the owner name when the team name is empty', () => {
    expect(marginSummary(team, [margin('', -5)])).toBe(
      'Wolves trails -owner by 5',
    );
  });
});
