import { act, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { afterEach, expect, vi } from 'vitest';

import LeagueQLLanding from '../landing-page';

import { setYahooAutoRefreshPref } from '@/features/connect_league/yahoo-auto-refresh-pref';
import {
  API,
  leagueMetadataError,
  server,
  sleeperNflState,
} from '@/test/msw/server';
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

/**
 * GET /leagues/:id returns 404 for the two pre-onboard lookups — the first Connect
 * (which reveals the credential fields) and the second Connect (which onboards) —
 * then 200 for the post-success read.
 */
function statefulGetLeague() {
  let calls = 0;
  return http.get(`${API}/leagues/:id`, () => {
    calls += 1;
    if (calls <= 2) {
      return HttpResponse.json({ detail: 'League not found' }, { status: 404 });
    }
    return HttpResponse.json({
      detail: 'Found league',
      data: { seasons: ['2026'], league_name: 'L', is_owner: true },
    });
  });
}

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

/**
 * Render the landing page and enter the league id (platform defaults to ESPN). The
 * ESPN credential fields are hidden until a lookup shows the league isn't onboarded,
 * so a single Connect click runs the existence check; a 404 reveals the fields.
 * Interactions run on real timers.
 */
async function lookupEspnLeague(leagueId: string) {
  const user = userEvent.setup();
  await renderRoute(
    <Routes>
      <Route path="/" element={<LeagueQLLanding />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
      <Route path="/connect_league" element={<div>CONNECT FORM</div>} />
    </Routes>,
    { route: '/' },
  );
  await user.type(await screen.findByPlaceholderText('League ID'), leagueId);
  await user.click(screen.getByRole('button', { name: /^connect$/i }));
}

/**
 * Connect a not-yet-onboarded ESPN league end to end. The credential fields are
 * gated behind the lookup, so this clicks Connect twice: the first click's 404
 * reveals the SWID/espn_s2 inputs, then — unless `skipCookies` — the cookies are
 * typed and Connect is clicked again to onboard. The second click's onboard/poll
 * runs under fake timers so `pollForCompletion`'s 1s interval can be fast-forwarded.
 */
async function connectEspnLeague(
  leagueId: string,
  opts: { skipCookies?: boolean } = {},
) {
  await lookupEspnLeague(leagueId);
  const user = userEvent.setup();
  // The first Connect resolved the existence check to 404 and revealed the fields.
  const swidInput = await screen.findByPlaceholderText('Enter your SWID');
  if (!opts.skipCookies) {
    await user.type(swidInput, 'swidcookie');
    await user.type(
      screen.getByPlaceholderText('Enter your ESPN S2 token'),
      's2cookie',
    );
  }
  vi.useFakeTimers();
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    await Promise.resolve();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(8000);
  });
}

/**
 * Simulate Yahoo's OAuth callback returning the browser to the landing page. The page
 * reads the YAHOO platform marker, linked flag, and league id from window.location.search
 * on mount and resumes onboarding inline. window.location is swapped for a URL so `search`
 * is real and
 * `href` is settable (the revoked path restarts OAuth). Fake timers are enabled before the
 * render so the resume's poll interval can be fast-forwarded — the resume runs during mount.
 */
async function returnFromYahoo(markers: Record<string, string>) {
  const search = new URLSearchParams({
    platform: 'YAHOO',
    ...markers,
  }).toString();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: new URL(`http://localhost/?${search}`),
  });
  vi.useFakeTimers();
  await renderRoute(
    <Routes>
      <Route path="/" element={<LeagueQLLanding />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/' },
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5000);
  });
}

defineFeature(feature, (test) => {
  test('ESPN credential fields stay hidden until the league is looked up', ({
    given,
    then,
    and,
  }) => {
    given('the landing connect form is open with ESPN selected', async () => {
      window.history.pushState({}, '', '/?connect=true');
      await renderRoute(
        <Routes>
          <Route path="/" element={<LeagueQLLanding />} />
        </Routes>,
        { route: '/' },
      );
    });

    then('the ESPN credential fields are not shown', async () => {
      // The connect form (League ID box) is present, but the SWID/espn_s2 inputs
      // stay hidden until a lookup shows the league isn't onboarded yet.
      expect(
        await screen.findByPlaceholderText('League ID'),
      ).toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText('Enter your SWID'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText('Enter your ESPN S2 token'),
      ).not.toBeInTheDocument();
    });

    and('the "League not added to LeagueQL yet" message is not shown', () => {
      expect(
        screen.queryByText(/League not added to LeagueQL yet/i),
      ).not.toBeInTheDocument();
    });
  });

  test('A first Connect on a not-yet-onboarded ESPN league reveals the credential fields', ({
    given,
    when,
    then,
    and,
  }) => {
    let onboardCalled = false;
    given('a not-yet-onboarded ESPN league', () => {
      server.use(
        http.get(`${API}/leagues/:id`, () =>
          HttpResponse.json({ detail: 'League not found' }, { status: 404 }),
        ),
        http.post(`${API}/leagues`, () => {
          onboardCalled = true;
          return HttpResponse.json(
            { detail: 'x', data: { correlation_id: 'c' } },
            { status: 201 },
          );
        }),
      );
      window.history.pushState({}, '', '/?connect=true');
    });
    when(
      /^I look up an ESPN league "(.*)" from the landing page$/,
      async (leagueId) => {
        await lookupEspnLeague(leagueId);
      },
    );
    then('the ESPN credential fields are shown', async () => {
      expect(
        await screen.findByPlaceholderText('Enter your SWID'),
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('Enter your ESPN S2 token'),
      ).toBeInTheDocument();
    });
    and('the "League not added to LeagueQL yet" message is shown', () => {
      expect(
        screen.getByText(/League not added to LeagueQL yet/i),
      ).toBeInTheDocument();
    });
    and('no ESPN onboard request was made', () => {
      expect(onboardCalled).toBe(false);
    });
  });

  test('Connecting an ESPN league I am not a member of shows already-onboarded guidance', ({
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

  test('Connecting a not-yet-onboarded ESPN league onboards in place', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: { season?: string } | null = null;
    given(
      /^a not-yet-onboarded ESPN league that will onboard successfully and the current season is "(.*)"$/,
      (season) => {
        server.use(
          sleeperNflState(season),
          statefulGetLeague(),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as { season?: string };
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
        window.history.pushState({}, '', '/?connect=true');
      },
    );
    when(
      /^I connect an ESPN league "(.*)" with cookies from the landing page$/,
      async (leagueId) => {
        await connectEspnLeague(leagueId);
      },
    );
    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
      // Onboarded in place — the caller was never routed to the connect form.
      expect(screen.queryByText('CONNECT FORM')).not.toBeInTheDocument();
    });
    and(/^the ESPN onboard request carried season "(.*)"$/, (season) => {
      expect(capturedBody?.season).toBe(season);
    });
  });

  test('The auto-derived season falls back to the clock when Sleeper is unavailable', ({
    given,
    when,
    then,
    and,
  }) => {
    let capturedBody: { season?: string } | null = null;
    given(
      'a not-yet-onboarded ESPN league that will onboard successfully and the Sleeper season endpoint is unavailable',
      () => {
        server.use(
          sleeperNflState(null),
          statefulGetLeague(),
          http.post(`${API}/leagues`, async ({ request }) => {
            capturedBody = (await request.json()) as { season?: string };
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
        window.history.pushState({}, '', '/?connect=true');
      },
    );
    when(
      /^I connect an ESPN league "(.*)" with cookies from the landing page$/,
      async (leagueId) => {
        await connectEspnLeague(leagueId);
      },
    );
    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
    and('the ESPN onboard request carried a 4-digit season', () => {
      expect(capturedBody?.season).toMatch(/^\d{4}$/);
    });
  });

  test('Connecting a not-yet-onboarded ESPN league without cookies shows an inline error', ({
    given,
    when,
    then,
    and,
  }) => {
    let onboardCalled = false;
    given('a not-yet-onboarded ESPN league', () => {
      server.use(
        http.get(`${API}/leagues/:id`, () =>
          HttpResponse.json({ detail: 'League not found' }, { status: 404 }),
        ),
        http.post(`${API}/leagues`, () => {
          onboardCalled = true;
          return HttpResponse.json(
            { detail: 'x', data: { correlation_id: 'c' } },
            { status: 201 },
          );
        }),
      );
      window.history.pushState({}, '', '/?connect=true');
    });
    when(
      /^I connect an ESPN league "(.*)" without cookies from the landing page$/,
      async (leagueId) => {
        await connectEspnLeague(leagueId, { skipCookies: true });
      },
    );
    // The error is set synchronously on submit (no request), so read it
    // synchronously — findByText would poll on real time under the fake timers
    // still active from the connect helper.
    then(/^I see invite-link guidance "(.*)"$/, (message) => {
      expect(screen.getByText(new RegExp(message))).toBeInTheDocument();
    });
    and('no ESPN onboard request was made', () => {
      expect(onboardCalled).toBe(false);
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

  test('Returning from Yahoo with a linked account resumes onboarding inline', ({
    given,
    when,
    then,
  }) => {
    given('onboarding a linked Yahoo league completes successfully', () => {
      server.use(onboardOk, jobStatus('COMPLETED'), getLeagueOk);
    });
    when(
      /^I return from Yahoo to the landing page with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await returnFromYahoo({ yahooLinked: '1', leagueId });
      },
    );
    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('Returning from Yahoo for an already-onboarded league routes straight in', ({
    given,
    when,
    then,
  }) => {
    given('the Yahoo league is already onboarded', () => {
      // No jobStatus handler: an already-onboarded league returns data:null, so the
      // return leg must skip polling and route straight into the existing league.
      server.use(onboardAlreadyOnboarded, getLeagueOk);
    });
    when(
      /^I return from Yahoo to the landing page with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await returnFromYahoo({ yahooLinked: '1', leagueId });
      },
    );
    then('I land on the league home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('The auto-refresh opt-in chosen before the redirect is applied on return', ({
    given,
    and,
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
    and('the Yahoo auto-refresh opt-in was stashed before the redirect', () => {
      // The opt-in is chosen before the consent redirect and stashed in sessionStorage;
      // the return leg consumes it (takeYahooAutoRefreshPref) and applies it on onboard.
      setYahooAutoRefreshPref(true);
    });
    when(
      /^I return from Yahoo to the landing page with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await returnFromYahoo({ yahooLinked: '1', leagueId });
      },
    );
    then('the Yahoo onboard request included auto-refresh', () => {
      expect(capturedBody?.autoRefresh).toBe(true);
    });
  });

  test('A revoked Yahoo link surfaced on return restarts the OAuth flow', ({
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
      },
    );
    when(
      /^I return from Yahoo to the landing page with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await returnFromYahoo({ yahooLinked: '1', leagueId });
      },
    );
    then('the Yahoo authorization is requested for that league', () => {
      expect(authorizeLeagueId).toBe('45.l.678');
      expect(window.location.href).toBe(
        'https://consent.yahoo.test/authorize?x=1',
      );
    });
  });

  test('A cancelled Yahoo link on return shows an inline retry alert', ({
    when,
    then,
  }) => {
    when(
      'I return from Yahoo to the landing page with a cancelled link',
      async () => {
        await returnFromYahoo({ yahooLinked: '0' });
      },
    );
    then(/^I see an inline alert "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
  });
});
