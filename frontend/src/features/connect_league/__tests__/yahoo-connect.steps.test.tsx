import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';

import LeagueConnect from '../league-connect';

import { API, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/connect_league/__tests__/yahoo-connect.feature',
);

async function renderReturn(markers: Record<string, string>) {
  // The page reads the Yahoo return markers from window.location.search directly.
  const search = new URLSearchParams({
    platform: 'YAHOO',
    ...markers,
  }).toString();
  window.history.pushState({}, '', `/connect_league?${search}`);
  await renderRoute(
    <Routes>
      <Route path="/connect_league" element={<LeagueConnect />} />
    </Routes>,
    { route: '/connect_league' },
  );
}

defineFeature(feature, (test) => {
  test('A successful Yahoo link shows the coming-soon notice', ({
    given,
    when,
    then,
    and,
  }) => {
    given('onboarding a Yahoo league returns the coming-soon signal', () => {
      server.use(
        http.post(`${API}/leagues`, () =>
          HttpResponse.json(
            { detail: 'coming soon', data: { code: 'YAHOO_COMING_SOON' } },
            { status: 200 },
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

    then(/^I see "(.*)"$/, async (text) => {
      expect(
        await screen.findByText(new RegExp(text, 'i')),
      ).toBeInTheDocument();
    });

    and(/^I see "(.*)"$/, async (text) => {
      expect(
        await screen.findByText(new RegExp(text, 'i')),
      ).toBeInTheDocument();
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

    then(/^I see "(.*)"$/, async (text) => {
      expect(
        await screen.findByText(new RegExp(text, 'i')),
      ).toBeInTheDocument();
    });
  });

  test('A cancelled Yahoo link offers a retry', ({ when, then, and }) => {
    when('I return from Yahoo with a cancelled link', async () => {
      await renderReturn({ yahooLinked: '0' });
    });

    then(/^I see "(.*)"$/, async (text) => {
      expect(
        await screen.findByText(new RegExp(text, 'i')),
      ).toBeInTheDocument();
    });

    and(/^I see a "(.*)" button$/, (name) => {
      expect(
        screen.getByRole('button', { name: new RegExp(name, 'i') }),
      ).toBeInTheDocument();
    });
  });
});
