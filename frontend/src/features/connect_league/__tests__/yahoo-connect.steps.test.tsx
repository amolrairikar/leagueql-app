import { act, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

import LeagueConnect from '../league-connect';

import { API, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/connect_league/__tests__/yahoo-connect.feature',
);

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

async function renderReturn(markers: Record<string, string>) {
  // The page reads the Yahoo return markers from window.location.search directly.
  const search = new URLSearchParams({
    platform: 'YAHOO',
    ...markers,
  }).toString();
  window.history.pushState({}, '', `/connect_league?${search}`);
  vi.useFakeTimers();
  await renderRoute(
    <Routes>
      <Route path="/connect_league" element={<LeagueConnect />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/connect_league' },
  );
  // Drive past pollForCompletion's 1s poll interval and flush resolved fetches/state.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5000);
  });
}

defineFeature(feature, (test) => {
  afterEach(() => vi.useRealTimers());

  test('A successful Yahoo link onboards and lands on the dashboard', ({
    given,
    when,
    then,
  }) => {
    given('onboarding a Yahoo league completes successfully', () => {
      server.use(onboardOk, jobStatus('COMPLETED'), getLeagueOk);
    });
    when(
      /^I return from Yahoo with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await renderReturn({ yahooLinked: '1', leagueId });
      },
    );
    then(/^I see "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
  });

  test('An already-onboarded Yahoo league lands on the dashboard', ({
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
      /^I return from Yahoo with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await renderReturn({ yahooLinked: '1', leagueId });
      },
    );
    then(/^I see "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
  });

  test('A revoked Yahoo token during onboarding prompts a reconnect', ({
    given,
    when,
    then,
  }) => {
    given('onboarding a Yahoo league fails with a re-link signal', () => {
      server.use(onboardOk, jobStatus('FAILED', 'YAHOO_AUTH'));
    });
    when(
      /^I return from Yahoo with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await renderReturn({ yahooLinked: '1', leagueId });
      },
    );
    then(/^I see "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
  });

  test('A lost Yahoo link prompts a reconnect', ({ given, when, then }) => {
    given('onboarding a Yahoo league is rejected as unlinked', () => {
      server.use(
        http.post(`${API}/leagues`, () =>
          HttpResponse.json(
            { detail: 'Link your Yahoo account first' },
            { status: 403 },
          ),
        ),
      );
    });
    when(
      /^I return from Yahoo with a linked account for league "(.*)"$/,
      async (leagueId) => {
        await renderReturn({ yahooLinked: '1', leagueId });
      },
    );
    then(/^I see "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
  });

  test('A cancelled Yahoo link offers a retry', ({ when, then, and }) => {
    when('I return from Yahoo with a cancelled link', async () => {
      await renderReturn({ yahooLinked: '0' });
    });
    then(/^I see "(.*)"$/, (text) => {
      expect(screen.getByText(new RegExp(text, 'i'))).toBeInTheDocument();
    });
    and(/^I see a "(.*)" button$/, (name) => {
      expect(
        screen.getByRole('button', { name: new RegExp(name, 'i') }),
      ).toBeInTheDocument();
    });
  });
});
