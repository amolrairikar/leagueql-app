import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { API, server } from '../../test/msw/server';
import {
  initFeatureFlags,
  isBillingEnabled,
  isEnabled,
  refreshFlags,
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

describe('feature-flags runtime resolution', () => {
  it('maps the GET /feature-flags payload onto the provider', async () => {
    server.use(
      http.get(`${API}/feature-flags`, () =>
        HttpResponse.json({
          detail: 'Feature flags',
          data: { billing: false, premium_feature: true },
        }),
      ),
    );
    await refreshFlags();
    expect(isBillingEnabled()).toBe(false);
    expect(isEnabled('premium_feature')).toBe(true);
  });

  it('keeps current flags when the endpoint errors (fail-safe)', async () => {
    setFlagsForTesting({ billing: true });
    server.use(
      http.get(`${API}/feature-flags`, () =>
        HttpResponse.json({ detail: 'boom' }, { status: 500 }),
      ),
    );
    await refreshFlags();
    expect(isBillingEnabled()).toBe(true);
  });

  it('keeps current flags on a network error', async () => {
    setFlagsForTesting({ billing: true });
    server.use(http.get(`${API}/feature-flags`, () => HttpResponse.error()));
    await refreshFlags();
    expect(isBillingEnabled()).toBe(true);
  });

  it('initFeatureFlags is a no-op under Vitest (never fetches)', async () => {
    setFlagsForTesting({ billing: true });
    // No MSW handler registered: a stray fetch would fail the suite
    // (onUnhandledRequest: 'error'). The Vitest guard must prevent it.
    await initFeatureFlags();
    expect(isBillingEnabled()).toBe(true);
  });
});
