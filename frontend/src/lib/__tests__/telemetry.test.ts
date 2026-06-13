import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  initTelemetry,
  isTelemetryEnabled,
  recordException,
  recordRouteChange,
  setTelemetryUser,
} from '../telemetry';

// Telemetry must stay OFF under Vitest: the component suite runs MSW with
// `onUnhandledRequest: 'error'`, so any stray exporter request would fail tests.
// vite.config sets VITE_API_URL='http://test.local', which the gate keys off.
afterEach(() => vi.unstubAllEnvs());

describe('telemetry gating', () => {
  it('stays disabled in the test env even when a proxy URL is configured', () => {
    vi.stubEnv('VITE_TRACES_URL', '/ingest/traces');
    expect(isTelemetryEnabled()).toBe(false);
  });

  it('is disabled when no proxy URL is configured', () => {
    vi.stubEnv('VITE_TRACES_URL', '');
    expect(isTelemetryEnabled()).toBe(false);
  });

  it('initTelemetry is a no-op that does not throw when disabled', () => {
    expect(() => initTelemetry()).not.toThrow();
  });

  it('span helpers are safe no-ops when disabled', () => {
    expect(() => setTelemetryUser('user_abc')).not.toThrow();
    expect(() => setTelemetryUser(null)).not.toThrow();
    expect(() => recordRouteChange('/home')).not.toThrow();
    expect(() => recordException(new Error('boom'))).not.toThrow();
  });
});
