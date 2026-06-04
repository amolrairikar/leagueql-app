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
        subscription_end_time: null,
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
});
