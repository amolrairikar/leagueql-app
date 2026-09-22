import { act, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { afterEach, expect, vi } from 'vitest';

import LeagueQLLanding from '../landing-page';

import { API, leagueMetadataError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/landing_page/__tests__/landing-connect.feature',
);

// Shared Yahoo onboarding handlers (POST /leagues). A linked caller gets a
// correlation_id (fresh onboard) or a null-data 200 (already onboarded); an
// unlinked caller is 403-gated ("link first").
const onboardOk = http.post(`${API}/leagues`, () =>
  HttpResponse.json(
    {
      detail: 'Successfully triggered onboarding',
      data: { correlation_id: 'corr-1' },
    },
    { status: 201 },
  ),
);

const onboardAlreadyOnboarded = http.post(`${API}/leagues`, () =>
  HttpResponse.json(
    { detail: 'League already onboarded', data: null },
    { status: 200 },
  ),
);

const onboardUnlinked = http.post(`${API}/leagues`, () =>
  HttpResponse.json(
    { detail: 'Link your Yahoo account first' },
    { status: 403 },
  ),
);

function jobStatus(status: string, failureCode: string | null = null) {
  return http.get(`${API}/jobs/:id`, () =>
    HttpResponse.json({
      detail: 'Found job status',
      data: { status, failure_code: failureCode, failure_reason: null },
    }),
  );
}

const getLeagueOk = http.get(`${API}/leagues/:id`, () =>
  HttpResponse.json({
    detail: 'League found',
    data: { seasons: ['2024'], league_name: 'L', is_owner: true },
  }),
);

// jsdom's window.location is non-configurable and navigation is unimplemented, so
// tests that expect a full-page consent redirect swap it for a URL (settable href,
// real search). Restored after every test.
const originalLocation = window.location;

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
  vi.useRealTimers();
});

/** Swap window.location so `href` is settable and the connect form is revealed. */
function swapLocationWithConnect() {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: new URL('http://localhost/?connect=true'),
  });
}

/**
 * Render the landing page, select Yahoo, enter the league id, and click Connect.
 * Interactions run on real timers; the click and the ensuing onboard/poll run under
 * fake timers so `pollForCompletion`'s 1s interval can be fast-forwarded.
 */
async function connectYahooLeague(
  leagueId: string,
  opts: { autoRefresh?: boolean } = {},
) {
  const user = userEvent.setup();
  await renderRoute(
    <Routes>
      <Route path="/" element={<LeagueQLLanding />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/' },
  );
  await user.click(await screen.findByRole('combobox'));
  await user.click(await screen.findByRole('option', { name: 'Yahoo' }));
  await user.type(screen.getByPlaceholderText('League ID'), leagueId);
  if (opts.autoRefresh) {
    await user.click(screen.getByRole('checkbox'));
  }
  vi.useFakeTimers();
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    await Promise.resolve();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5000);
  });
}

defineFeature(feature, (test) => {
  test('Connecting an ESPN league I am not a member of shows invite-link guidance', ({
    given,
    when,
    then,
  }) => {
    given('the ESPN league read is member-gated for me', async () => {
      // The read is a member-gated 403 and there is no cookie self-serve path —
      // the caller is directed to an owner's invite link.
      server.use(leagueMetadataError(403));
      window.history.pushState({}, '', '/?connect=true');
      await renderRoute(
        <Routes>
          <Route path="/" element={<LeagueQLLanding />} />
          <Route path="/home" element={<div>HOME PAGE</div>} />
        </Routes>,
        { route: '/' },
      );
    });

    when('I submit an ESPN league ID from the landing page', async () => {
      // Platform defaults to ESPN on the landing connect form.
      await userEvent.type(
        await screen.findByPlaceholderText('League ID'),
        '100',
      );
      await userEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    });

    then(/^I see invite-link guidance "(.*)"$/, async (message) => {
      expect(await screen.findByText(new RegExp(message))).toBeInTheDocument();
    });
  });

  test('The connect form offers Yahoo as a selectable platform', ({
    given,
    when,
    then,
  }) => {
    given('the landing connect form is open', async () => {
      window.history.pushState({}, '', '/?connect=true');
      await renderRoute(
        <Routes>
          <Route path="/" element={<LeagueQLLanding />} />
        </Routes>,
        { route: '/' },
      );
    });

    when('I open the platform dropdown', async () => {
      // The platform Select trigger is the only combobox on the connect form.
      await userEvent.click(await screen.findByRole('combobox'));
    });

    then('Yahoo is offered as a selectable platform', async () => {
      expect(
        await screen.findByRole('option', { name: 'Yahoo' }),
      ).toBeInTheDocument();
    });
  });

  test('Connecting a Yahoo league I have not linked starts the OAuth flow', ({
    given,
    when,
    then,
  }) => {
    let authorizeLeagueId: string | null = null;

    given(
      'onboarding a Yahoo league is rejected as unlinked and the authorize endpoint returns a consent URL',
      () => {
        server.use(
          onboardUnlinked,
          http.get(`${API}/leagues/yahoo/oauth/authorize`, ({ request }) => {
            authorizeLeagueId = new URL(request.url).searchParams.get(
              'leagueId',
            );
            return HttpResponse.json({
              detail: 'ok',
              data: {
                authorize_url: 'https://consent.yahoo.test/authorize?x=1',
              },
            });
          }),
        );
        swapLocationWithConnect();
      },
    );

    when(
      /^I connect a Yahoo league "(.*)" from the landing page$/,
      async (leagueId) => {
        await connectYahooLeague(leagueId);
      },
    );

    then('the Yahoo authorization is requested for that league', () => {
      expect(authorizeLeagueId).toBe('45.l.678');
      expect(window.location.href).toBe(
        'https://consent.yahoo.test/authorize?x=1',
      );
    });
  });

  test('Connecting a Yahoo league I have already linked onboards in place', ({
    given,
    when,
    then,
  }) => {
    given('onboarding a linked Yahoo league completes successfully', () => {
      server.use(onboardOk, jobStatus('COMPLETED'), getLeagueOk);
      window.history.pushState({}, '', '/?connect=true');
    });

    when(
      /^I connect a Yahoo league "(.*)" from the landing page$/,
      async (leagueId) => {
        await connectYahooLeague(leagueId);
      },
    );

    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('Connecting an already-onboarded Yahoo league routes straight in', ({
    given,
    when,
    then,
  }) => {
    given('the Yahoo league is already onboarded', () => {
      // No jobStatus handler: an already-onboarded league returns data:null, so the
      // form must skip polling and route straight into the existing league.
      server.use(onboardAlreadyOnboarded, getLeagueOk);
      window.history.pushState({}, '', '/?connect=true');
    });

    when(
      /^I connect a Yahoo league "(.*)" from the landing page$/,
      async (leagueId) => {
        await connectYahooLeague(leagueId);
      },
    );

    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('A revoked Yahoo link restarts the OAuth flow', ({
    given,
    when,
    then,
  }) => {
    let authorizeLeagueId: string | null = null;

    given(
      'onboarding a linked Yahoo league fails with a re-link signal and the authorize endpoint returns a consent URL',
      () => {
        server.use(
          onboardOk,
          jobStatus('FAILED', 'YAHOO_AUTH'),
          http.get(`${API}/leagues/yahoo/oauth/authorize`, ({ request }) => {
            authorizeLeagueId = new URL(request.url).searchParams.get(
              'leagueId',
            );
            return HttpResponse.json({
              detail: 'ok',
              data: {
                authorize_url: 'https://consent.yahoo.test/authorize?x=1',
              },
            });
          }),
        );
        swapLocationWithConnect();
      },
    );

    when(
      /^I connect a Yahoo league "(.*)" from the landing page$/,
      async (leagueId) => {
        await connectYahooLeague(leagueId);
      },
    );

    then('the Yahoo authorization is requested for that league', () => {
      expect(authorizeLeagueId).toBe('45.l.678');
      expect(window.location.href).toBe(
        'https://consent.yahoo.test/authorize?x=1',
      );
    });
  });

  test('Enabling auto-refresh when connecting a linked Yahoo league sends the opt-in', ({
    given,
    when,
    then,
  }) => {
    let capturedBody: { autoRefresh?: boolean } | null = null;
    given('onboarding a linked Yahoo league completes successfully', () => {
      server.use(
        getLeagueOk,
        http.post(`${API}/leagues`, async ({ request }) => {
          capturedBody = (await request.json()) as { autoRefresh?: boolean };
          return HttpResponse.json(
            {
              detail: 'Successfully triggered onboarding',
              data: { correlation_id: 'corr-1' },
            },
            { status: 201 },
          );
        }),
        jobStatus('COMPLETED'),
      );
    });
    when(
      /^I connect a Yahoo league "(.*)" with auto-refresh enabled$/,
      async (leagueId) => {
        await connectYahooLeague(leagueId, { autoRefresh: true });
      },
    );
    then('the Yahoo onboard request included auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBe(true);
    });
  });
});
