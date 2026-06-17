import { OpenFeature } from '@openfeature/web-sdk';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

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

  it('does not swap the provider when the refreshed flags are unchanged', async () => {
    // Apply a known flag set, then have the endpoint return the SAME values.
    setFlagsForTesting({ billing: true, premium_feature: false });
    const setProvider = vi.spyOn(OpenFeature, 'setProvider');
    server.use(
      http.get(`${API}/feature-flags`, () =>
        HttpResponse.json({
          detail: 'Feature flags',
          // Key order differs from the applied map to prove the comparison is
          // order-independent (a no-op refresh must not depend on JSON order).
          data: { premium_feature: false, billing: true },
        }),
      ),
    );
    await refreshFlags();
    // No provider swap => no PROVIDER_READY/CONFIGURATION_CHANGED => no remount.
    expect(setProvider).not.toHaveBeenCalled();
    expect(isBillingEnabled()).toBe(true);
    setProvider.mockRestore();
  });

  it('swaps the provider when a refreshed flag value changes', async () => {
    setFlagsForTesting({ billing: true, premium_feature: false });
    const setProvider = vi.spyOn(OpenFeature, 'setProvider');
    server.use(
      http.get(`${API}/feature-flags`, () =>
        HttpResponse.json({
          detail: 'Feature flags',
          data: { billing: true, premium_feature: true },
        }),
      ),
    );
    await refreshFlags();
    expect(setProvider).toHaveBeenCalledTimes(1);
    expect(isEnabled('premium_feature')).toBe(true);
    setProvider.mockRestore();
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
