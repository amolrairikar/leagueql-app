import { act, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { afterEach, vi } from 'vitest';

import LeagueConnect from '../league-connect';

import { API, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/connect_league/__tests__/connect-league.feature',
);

/** GET /leagues/:id returns 404 first (drives ONBOARD), then 200 (post-success read). */
function statefulGetLeague() {
  let calls = 0;
  return http.get(`${API}/leagues/:id`, () => {
    calls += 1;
    if (calls === 1) {
      return HttpResponse.json({ detail: 'League not found' }, { status: 404 });
    }
    return HttpResponse.json({
      detail: 'Found league',
      data: {
        seasons: ['2024'],
        league_name: 'L',
      },
    });
  });
}

const onboardOk = http.post(`${API}/leagues`, () =>
  HttpResponse.json(
    {
      detail: 'Successfully triggered onboarding',
      data: { correlation_id: 'corr-1' },
    },
    { status: 201 },
  ),
);

function jobStatus(status: string, failureReason: string | null = null) {
  return http.get(`${API}/jobs/:id`, () =>
    HttpResponse.json({
      detail: 'Found job status',
      data: { status, failure_code: null, failure_reason: failureReason },
    }),
  );
}

async function renderConnect() {
  // The form reads the platform from window.location.search directly, so preset
  // Sleeper there (Sleeper needs only a league ID — no season/cookies).
  window.history.pushState({}, '', '/connect_league?platform=sleeper');
  await renderRoute(
    <Routes>
      <Route path="/connect_league" element={<LeagueConnect />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/connect_league' },
  );
}

async function onboardFlow(leagueId: string) {
  vi.useFakeTimers();
  await renderConnect();
  await submitLeague(leagueId);
}

async function submitLeague(leagueId: string) {
  await act(async () => {
    fireEvent.change(screen.getByPlaceholderText('Enter your league ID'), {
      target: { value: leagueId },
    });
    await Promise.resolve();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    await Promise.resolve();
  });
  // Drive past the 5s initial delay + the 1s poll interval and flush the
  // resolved fetches/state updates in between.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(8000);
  });
}

async function connectEspnFlow(leagueId: string) {
  vi.useFakeTimers();
  window.history.pushState({}, '', '/connect_league?platform=espn');
  await renderRoute(
    <Routes>
      <Route path="/connect_league" element={<LeagueConnect />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/connect_league' },
  );
  await act(async () => {
    fireEvent.change(screen.getByPlaceholderText('Enter your league ID'), {
      target: { value: leagueId },
    });
    fireEvent.change(
      screen.getByPlaceholderText(
        'Enter the latest season your league was active',
      ),
      { target: { value: '2024' } },
    );
    fireEvent.change(screen.getByPlaceholderText('Enter your SWID'), {
      target: { value: '{SWID}' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your ESPN S2 token'), {
      target: { value: 's2cookie' },
    });
    await Promise.resolve();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    await Promise.resolve();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(8000);
  });
}

defineFeature(feature, (test) => {
  // Restore real timers after every scenario; a no-op when they were never faked
  // (the validation scenario uses real timers so userEvent works).
  afterEach(() => vi.useRealTimers());

  test('Submitting without a league ID shows a validation error', ({
    given,
    when,
    then,
  }) => {
    given('the connect league form is open', async () => {
      await renderRoute(<LeagueConnect />, { route: '/connect_league' });
    });
    when('I submit the form without a league ID', async () => {
      await userEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    });
    then(/^I see a validation error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });

  test('A successful onboard polls to completion and routes home', ({
    given,
    when,
    then,
  }) => {
    given('onboarding will complete successfully', () => {
      server.use(statefulGetLeague(), onboardOk, jobStatus('COMPLETED'));
    });
    when(/^I onboard Sleeper league "(.*)"$/, async (leagueId) => {
      await onboardFlow(leagueId);
    });
    then('I am routed to the home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('A failed job surfaces the backend failure reason', ({
    given,
    when,
    then,
  }) => {
    given(/^onboarding will fail with reason "(.*)"$/, (reason) => {
      server.use(statefulGetLeague(), onboardOk, jobStatus('FAILED', reason));
    });
    when(/^I onboard Sleeper league "(.*)"$/, async (leagueId) => {
      await onboardFlow(leagueId);
    });
    then(/^I see a failure message "(.*)"$/, (reason) => {
      expect(screen.getByText(new RegExp(reason))).toBeInTheDocument();
    });
  });

  test('Opening an already-onboarded league as a non-owner routes home without refreshing', ({
    given,
    when,
    then,
    and,
  }) => {
    let onboardCalled = false;
    given('the league is already onboarded and I am not its owner', () => {
      server.use(
        http.get(`${API}/leagues/:id`, () =>
          HttpResponse.json({
            detail: 'Found league',
            data: {
              seasons: ['2024'],
              league_name: 'L',
              is_owner: false,
            },
          }),
        ),
        http.post(`${API}/leagues`, () => {
          onboardCalled = true;
          return HttpResponse.json(
            { detail: 'x', data: { correlation_id: 'c' } },
            { status: 201 },
          );
        }),
      );
    });
    when(/^I onboard Sleeper league "(.*)"$/, async (leagueId) => {
      await onboardFlow(leagueId);
    });
    then('I am routed to the home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
    and('no onboard or refresh request was made', () => {
      expect(onboardCalled).toBe(false);
    });
  });

  test('Connecting to an ESPN league I am not yet a member of verifies membership', ({
    given,
    when,
    then,
    and,
  }) => {
    let verifyCalled = false;
    given('the ESPN league is onboarded but I am not yet a member', () => {
      let getCalls = 0;
      server.use(
        http.get(`${API}/leagues/:id`, () => {
          getCalls += 1;
          // First read (existence check) is a member-gated 403; after verifying,
          // the post-join read succeeds.
          if (getCalls === 1) {
            return HttpResponse.json(
              { detail: 'Not a member of this league' },
              { status: 403 },
            );
          }
          return HttpResponse.json({
            detail: 'Found league',
            data: {
              seasons: ['2024'],
              league_name: 'L',
              is_owner: false,
            },
          });
        }),
        http.post(`${API}/leagues/:id/verify-membership`, () => {
          verifyCalled = true;
          return HttpResponse.json({ detail: 'Membership verified' });
        }),
      );
    });
    when(/^I connect ESPN league "(.*)"$/, async (leagueId) => {
      await connectEspnFlow(leagueId);
    });
    then('I am routed to the home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
    and('membership verification was requested', () => {
      expect(verifyCalled).toBe(true);
    });
  });
});
