import { act, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, vi } from 'vitest';

import { RefreshLeagueDialog } from '../refresh-league-dialog';

import { API, server, sleeperNflState } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/refresh-league.feature',
);

const espnLeague = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

const jobCompleted = http.get(`${API}/jobs/:id`, () =>
  HttpResponse.json({
    detail: 'Found job status',
    data: { status: 'COMPLETED', failure_code: null, failure_reason: null },
  }),
);

// The post-success re-read of the league (to refresh the stored season list).
const getLeagueOk = http.get(`${API}/leagues/:id`, () =>
  HttpResponse.json({
    detail: 'Found league',
    data: { seasons: ['2024', '2026'], league_name: 'L', is_owner: true },
  }),
);

defineFeature(feature, (test) => {
  let reload: ReturnType<typeof vi.fn>;
  const originalLocation = window.location;

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    });
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  function stubReload() {
    reload = vi.fn();
    // jsdom's window.location is non-configurable and reload is unimplemented, so
    // swap the whole location for an object with a spyable reload.
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, reload },
    });
  }

  async function renderDialog(reauth = false) {
    await renderRoute(
      <RefreshLeagueDialog open onOpenChange={vi.fn()} reauth={reauth} />,
      { league: espnLeague },
    );
  }

  /** Fill the SWID/espn_s2 inputs (real timers), then submit under fake timers. */
  async function enterCookiesAndRefresh(
    opts: { autoRefresh?: boolean; reauth?: boolean } = {},
  ) {
    const user = userEvent.setup();
    await renderDialog(opts.reauth);
    await user.type(
      screen.getByPlaceholderText('Enter your SWID'),
      'swidcookie',
    );
    await user.type(
      screen.getByPlaceholderText('Enter your ESPN S2 token'),
      's2cookie',
    );
    if (opts.autoRefresh) {
      await user.click(
        screen.getByRole('checkbox', {
          name: /enable automatic weekly refresh/i,
        }),
      );
    }
    vi.useFakeTimers();
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: /^refresh league$/i }),
      );
      await Promise.resolve();
    });
    // Drive past the 5s initial delay + the 1s poll interval and the ensuing
    // re-read, flushing resolved fetches in between.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(8000);
    });
  }

  test('Refreshing with cookies pulls the latest data in place', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: {
      season?: string;
      swid?: string;
      s2?: string;
      autoRefresh?: boolean;
    } | null = null;
    given(
      /^refreshing my ESPN league will complete successfully and the current season is "(.*)"$/,
      (season) => {
        stubReload();
        server.use(
          sleeperNflState(season),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as typeof capturedBody;
            return HttpResponse.json(
              {
                detail: 'Successfully triggered refresh',
                data: { correlation_id: 'corr-1' },
              },
              { status: 201 },
            );
          }),
          jobCompleted,
          getLeagueOk,
        );
      },
    );
    when('I enter my ESPN cookies and refresh from the dialog', async () => {
      await enterCookiesAndRefresh();
    });
    then(/^the refresh request carried season "(.*)"$/, (season) => {
      expect(capturedBody?.season).toBe(season);
      expect(capturedBody?.swid).toBe('swidcookie');
      expect(capturedBody?.s2).toBe('s2cookie');
    });
    and('the refresh request did not opt into auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBeFalsy();
    });
    and('the dashboard reloads with the fresh data', () => {
      expect(reload).toHaveBeenCalled();
    });
  });

  test('Enabling auto-refresh in the dialog sends the opt-in', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: { autoRefresh?: boolean } | null = null;
    given(
      /^refreshing my ESPN league will complete successfully and the current season is "(.*)"$/,
      (season) => {
        stubReload();
        server.use(
          sleeperNflState(season),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as { autoRefresh?: boolean };
            return HttpResponse.json(
              {
                detail: 'Successfully triggered refresh',
                data: { correlation_id: 'corr-1' },
              },
              { status: 201 },
            );
          }),
          jobCompleted,
          getLeagueOk,
        );
      },
    );
    when(
      'I enter my ESPN cookies, enable auto-refresh, and refresh from the dialog',
      async () => {
        await enterCookiesAndRefresh({ autoRefresh: true });
      },
    );
    then('the refresh request opted into auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBe(true);
    });
    and('the dashboard reloads with the fresh data', () => {
      expect(reload).toHaveBeenCalled();
    });
  });

  test('Updating rejected cookies keeps the league on auto-refresh', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: { autoRefresh?: boolean } | null = null;
    given(
      /^refreshing my ESPN league will complete successfully and the current season is "(.*)"$/,
      (season) => {
        stubReload();
        server.use(
          sleeperNflState(season),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as { autoRefresh?: boolean };
            return HttpResponse.json(
              {
                detail: 'Successfully triggered refresh',
                data: { correlation_id: 'corr-1' },
              },
              { status: 201 },
            );
          }),
          jobCompleted,
          getLeagueOk,
        );
      },
    );
    when(
      'I enter my ESPN cookies in the Update ESPN Cookies dialog and submit without touching the opt-in',
      async () => {
        await enterCookiesAndRefresh({ reauth: true });
      },
    );
    then('the refresh request opted into auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBe(true);
    });
    and('the dashboard reloads with the fresh data', () => {
      expect(reload).toHaveBeenCalled();
    });
  });

  test('A refresh blocked by the weekly cooldown shows a benign notice', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      /^refreshing my ESPN league is blocked by the weekly cooldown with message "(.*)"$/,
      (message) => {
        stubReload();
        server.use(
          sleeperNflState('2026'),
          http.post(`${API}/leagues`, () =>
            HttpResponse.json({ detail: message }, { status: 429 }),
          ),
        );
      },
    );
    when('I enter my ESPN cookies and refresh from the dialog', async () => {
      await enterCookiesAndRefresh();
    });
    then(/^I see the notice title "(.*)"$/, (title) => {
      expect(screen.getByText(title)).toBeInTheDocument();
    });
    and('the dashboard does not reload', () => {
      expect(reload).not.toHaveBeenCalled();
    });
  });

  test('An opted-in refresh blocked by the weekly cooldown still enables auto-refresh', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: { autoRefresh?: boolean } | null = null;
    given(
      /^refreshing my ESPN league is blocked by the weekly cooldown with message "(.*)"$/,
      (message) => {
        stubReload();
        server.use(
          sleeperNflState('2026'),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as { autoRefresh?: boolean };
            return HttpResponse.json({ detail: message }, { status: 429 });
          }),
        );
      },
    );
    when(
      'I enter my ESPN cookies, enable auto-refresh, and refresh from the dialog',
      async () => {
        await enterCookiesAndRefresh({ autoRefresh: true });
      },
    );
    then('the refresh request opted into auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBe(true);
    });
    and(/^I see the notice title "(.*)"$/, (title) => {
      expect(screen.getByText(title)).toBeInTheDocument();
      expect(screen.getByText(/once per week/)).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /^refresh league$/i }),
      ).not.toBeInTheDocument();
    });
    and('the dashboard does not reload', () => {
      expect(reload).not.toHaveBeenCalled();
    });
    when('I close the dialog with Done', () => {
      fireEvent.click(screen.getByRole('button', { name: /^done$/i }));
    });
    then('the dashboard reloads with the fresh data', () => {
      expect(reload).toHaveBeenCalled();
    });
  });

  test('An opted-in blocked refresh with rejected cookies shows the backend error', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      /^refreshing my ESPN league is rejected with status 400 and message "(.*)"$/,
      (message) => {
        stubReload();
        server.use(
          sleeperNflState('2026'),
          http.post(`${API}/leagues`, () =>
            HttpResponse.json({ detail: message }, { status: 400 }),
          ),
        );
      },
    );
    when(
      'I enter my ESPN cookies, enable auto-refresh, and refresh from the dialog',
      async () => {
        await enterCookiesAndRefresh({ autoRefresh: true });
      },
    );
    then(/^I see an inline error "(.*)"$/, (message) => {
      expect(screen.getByText(new RegExp(message))).toBeInTheDocument();
      expect(screen.getByText('Refresh Failed')).toBeInTheDocument();
    });
    and('the dashboard does not reload', () => {
      expect(reload).not.toHaveBeenCalled();
    });
  });

  test('Refreshing without cookies shows an inline error', ({
    given,
    when,
    then,
    and,
  }) => {
    let onboardCalled = false;
    given('I open the refresh dialog for my ESPN league', () => {
      stubReload();
      server.use(
        sleeperNflState('2026'),
        http.post(`${API}/leagues`, () => {
          onboardCalled = true;
          return HttpResponse.json(
            { detail: 'x', data: { correlation_id: 'c' } },
            { status: 201 },
          );
        }),
      );
    });
    when('I refresh from the dialog without entering cookies', async () => {
      await renderDialog();
      await userEvent.click(
        screen.getByRole('button', { name: /^refresh league$/i }),
      );
    });
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(new RegExp(message))).toBeInTheDocument();
    });
    and('no refresh request was made', () => {
      expect(onboardCalled).toBe(false);
      expect(reload).not.toHaveBeenCalled();
    });
  });
});
