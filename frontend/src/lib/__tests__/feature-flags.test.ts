import { describe, expect, it } from 'vitest';

import {
  isBillingEnabled,
  isEnabled,
  setFlagsForTesting,
} from '../feature-flags';

// The global test setup (src/test/setup.ts) defaults the billing flag ON before
// each test; these tests assert the helper reflects explicit overrides.
describe('feature-flags', () => {
  it('reports billing on when enabled', () => {
    setFlagsForTesting({ billing: true });
    expect(isBillingEnabled()).toBe(true);
  });

  it('reports billing off when disabled', () => {
    setFlagsForTesting({ billing: false });
    expect(isBillingEnabled()).toBe(false);
  });

  it('defaults an unknown flag to false', () => {
    setFlagsForTesting({ billing: true });
    expect(isEnabled('does-not-exist')).toBe(false);
  });

  it('evaluates an arbitrary flag', () => {
    setFlagsForTesting({ some_feature: true });
    expect(isEnabled('some_feature')).toBe(true);
    // billing is absent from this map, so it falls back to off.
    expect(isBillingEnabled()).toBe(false);
  });
});
