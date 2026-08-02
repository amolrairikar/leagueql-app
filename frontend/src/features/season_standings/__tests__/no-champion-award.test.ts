import { describe, expect, it } from 'vitest';

import { noChampionAward } from '../season-champion-award';

// The Season Champion award falls back to this label when no champion is recorded. Only the
// most recent season can still be in progress ("TBD"); an earlier completed season shows "N/A".
describe('noChampionAward', () => {
  it('shows an in-progress label for the latest season', () => {
    expect(noChampionAward(true)).toEqual({
      title: 'TBD',
      subtitle: 'Season in progress',
    });
  });

  it('shows a no-champion label for a completed earlier season', () => {
    expect(noChampionAward(false)).toEqual({
      title: 'N/A',
      subtitle: 'No champion',
    });
  });
});
