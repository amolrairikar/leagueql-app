import { describe, expect, it, vi } from 'vitest';

import type { SubscriptionState } from '../use-subscription';
import { deriveState, pollUntilActive } from '../use-subscription';

const DAY_MS = 24 * 60 * 60 * 1000;

const noSleep = () => Promise.resolve();

function isoIn(days: number): string {
  return new Date(Date.now() + days * DAY_MS).toISOString();
}

describe('deriveState', () => {
  it('treats a far-future end time as active and not expiring', () => {
    const state = deriveState(isoIn(30));
    expect(state.isActive).toBe(true);
    expect(state.expiringSoon).toBe(false);
    expect(state.activating).toBe(false);
  });

  it('flags a soon-to-lapse subscription as expiringSoon', () => {
    const state = deriveState(isoIn(3));
    expect(state.isActive).toBe(true);
    expect(state.expiringSoon).toBe(true);
  });

  it('treats a past end time as expired', () => {
    expect(deriveState(isoIn(-1)).isActive).toBe(false);
  });

  it('treats an absent end time as expired', () => {
    expect(deriveState(undefined).isActive).toBe(false);
  });

  it('treats an unparseable end time as expired', () => {
    expect(deriveState('not-a-date').isActive).toBe(false);
  });

  it('preserves the raw end time for display', () => {
    const iso = isoIn(1);
    expect(deriveState(iso).endTime).toBe(iso);
  });
});

describe('pollUntilActive', () => {
  const expired: SubscriptionState = {
    loading: false,
    isActive: false,
    expiringSoon: false,
    activating: false,
  };
  const active: SubscriptionState = {
    loading: false,
    isActive: true,
    expiringSoon: false,
    activating: false,
  };

  it('returns immediately when the first read is active', async () => {
    const fetchState = vi.fn().mockResolvedValue(active);
    const res = await pollUntilActive(fetchState, {
      attempts: 5,
      intervalMs: 1,
      sleep: noSleep,
    });
    expect(res.isActive).toBe(true);
    expect(fetchState).toHaveBeenCalledTimes(1);
  });

  it('polls until the subscription reads active', async () => {
    const fetchState = vi
      .fn()
      .mockResolvedValueOnce(expired)
      .mockResolvedValueOnce(expired)
      .mockResolvedValueOnce(active);
    const res = await pollUntilActive(fetchState, {
      attempts: 5,
      intervalMs: 1,
      sleep: noSleep,
    });
    expect(res.isActive).toBe(true);
    expect(fetchState).toHaveBeenCalledTimes(3);
  });

  it('gives up after the attempt budget, returning the last state', async () => {
    const fetchState = vi.fn().mockResolvedValue(expired);
    const res = await pollUntilActive(fetchState, {
      attempts: 3,
      intervalMs: 1,
      sleep: noSleep,
    });
    expect(res.isActive).toBe(false);
    expect(fetchState).toHaveBeenCalledTimes(3);
  });
});
