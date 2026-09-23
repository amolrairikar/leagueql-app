import { describe, expect, it } from 'vitest';

import { latestSeason, seasonQuery } from '../season';

import { ApiError } from '@/lib/api-client';

describe('latestSeason', () => {
  it('returns the highest season by numeric value regardless of order', () => {
    expect(latestSeason(['2021', '2024', '2019'])).toBe('2024');
  });

  it('does not mutate the input array', () => {
    const seasons = ['2021', '2024', '2019'];
    latestSeason(seasons);
    expect(seasons).toEqual(['2021', '2024', '2019']);
  });

  it('returns an empty string for no seasons', () => {
    expect(latestSeason([])).toBe('');
  });
});

describe('seasonQuery', () => {
  it('resolves to an empty success when not ready, without calling fetch', async () => {
    let called = false;
    const result = await seasonQuery(
      false,
      () => {
        called = true;
        return Promise.resolve({ data: [1, 2, 3] });
      },
      'boom',
    );
    expect(called).toBe(false);
    expect(result).toEqual({ ok: true, data: [] });
  });

  it('resolves to a success with the fetched data when ready', async () => {
    const result = await seasonQuery(
      true,
      () => Promise.resolve({ data: [1, 2, 3] }),
      'boom',
    );
    expect(result).toEqual({ ok: true, data: [1, 2, 3] });
  });

  it('surfaces the backend message for a 4xx failure', async () => {
    const result = await seasonQuery(
      true,
      () => Promise.reject(new ApiError(404, 'Not Found', 'bad league')),
      'fallback message',
    );
    expect(result).toEqual({ ok: false, error: 'bad league' });
  });

  it('falls back to the caller message for a 5xx failure', async () => {
    const result = await seasonQuery(
      true,
      () =>
        Promise.reject(
          new ApiError(500, 'Server Error', 'Internal Server Error'),
        ),
      'fallback message',
    );
    expect(result).toEqual({ ok: false, error: 'fallback message' });
  });
});
