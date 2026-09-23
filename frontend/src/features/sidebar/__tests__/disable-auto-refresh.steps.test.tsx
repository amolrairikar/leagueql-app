import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, vi } from 'vitest';

import { DisableAutoRefreshDialog } from '../disable-auto-refresh-dialog';

import { API, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/disable-auto-refresh.feature',
);

const espnLeague = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

defineFeature(feature, (test) => {
  let reload: ReturnType<typeof vi.fn>;
  const originalLocation = window.location;

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    });
    vi.restoreAllMocks();
  });

  function stubReload() {
    reload = vi.fn();
    // jsdom's window.location is non-configurable and reload is unimplemented, so
    // swap the whole location for an object with a spyable reload — this lets the
    // success path (clearApiCache + reload) be asserted.
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, reload },
    });
  }

  async function renderDialog() {
    await renderRoute(
      <DisableAutoRefreshDialog open onOpenChange={vi.fn()} />,
      { league: espnLeague },
    );
  }

  test('Confirming turns auto-refresh off', ({ given, when, then, and }) => {
    let capturedBody: { enabled?: boolean } | null = null;

    given('I own an ESPN league enrolled in auto-refresh', () => {
      stubReload();
      server.use(
        http.put(`${API}/leagues/:id/auto-refresh`, async ({ request }) => {
          capturedBody = (await request.json()) as { enabled?: boolean };
          return HttpResponse.json({
            detail: 'Auto-refresh disabled',
            data: { auto_refresh_enabled: false },
          });
        }),
      );
    });
    when('I confirm turning auto-refresh off', async () => {
      await renderDialog();
      await userEvent.click(
        screen.getByRole('button', { name: /turn off auto-refresh/i }),
      );
    });
    then('the app sends a disable request with enabled false', async () => {
      await vi.waitFor(() => expect(capturedBody).not.toBeNull());
      expect(capturedBody?.enabled).toBe(false);
    });
    and('the page reloads', async () => {
      await vi.waitFor(() => expect(reload).toHaveBeenCalled());
    });
  });

  test('Cancelling sends no request', ({ given, when, then }) => {
    let called = false;

    given('I own an ESPN league enrolled in auto-refresh', () => {
      stubReload();
      server.use(
        http.put(`${API}/leagues/:id/auto-refresh`, () => {
          called = true;
          return HttpResponse.json({
            detail: 'Auto-refresh disabled',
            data: { auto_refresh_enabled: false },
          });
        }),
      );
    });
    when('I cancel the turn-off dialog', async () => {
      await renderDialog();
      await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    });
    then('no disable request is sent', () => {
      expect(called).toBe(false);
      expect(reload).not.toHaveBeenCalled();
    });
  });

  test('A failed disable shows an error and keeps the dialog open', ({
    given,
    when,
    then,
    and,
  }) => {
    given('turning auto-refresh off will fail', () => {
      stubReload();
      server.use(
        http.put(`${API}/leagues/:id/auto-refresh`, () =>
          HttpResponse.json(
            { detail: 'Internal Server Error' },
            { status: 500 },
          ),
        ),
      );
    });
    when('I confirm turning auto-refresh off', async () => {
      await renderDialog();
      await userEvent.click(
        screen.getByRole('button', { name: /turn off auto-refresh/i }),
      );
    });
    then('I see an inline error and the dialog stays open', async () => {
      expect(
        await screen.findByText('Internal Server Error'),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /cancel/i }),
      ).toBeInTheDocument();
    });
    and('the page does not reload', () => {
      expect(reload).not.toHaveBeenCalled();
    });
  });
});
