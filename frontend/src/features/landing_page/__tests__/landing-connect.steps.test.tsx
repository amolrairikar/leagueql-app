import { screen } from '@testing-library/react';
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

  test('Connecting a Yahoo league starts the OAuth flow', ({
    given,
    when,
    then,
  }) => {
    // jsdom's window.location.href is non-configurable and navigation is unimplemented,
    // so swap window.location for a URL (settable href, real search) to observe the
    // full-page redirect. Restored after each test.
    const originalLocation = window.location;
    afterEach(() => {
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      });
    });

    let authorizeLeagueId: string | null = null;

    given('the Yahoo authorize endpoint returns a consent URL', () => {
      server.use(
        http.get(`${API}/auth/yahoo/authorize`, ({ request }) => {
          authorizeLeagueId = new URL(request.url).searchParams.get('leagueId');
          return HttpResponse.json({
            detail: 'ok',
            data: { authorize_url: 'https://consent.yahoo.test/authorize?x=1' },
          });
        }),
      );
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: new URL('http://localhost/?connect=true'),
      });
    });

    when(
      /^I connect a Yahoo league "(.*)" from the landing page$/,
      async (leagueId) => {
        await renderRoute(
          <Routes>
            <Route path="/" element={<LeagueQLLanding />} />
          </Routes>,
          { route: '/' },
        );
        await userEvent.click(await screen.findByRole('combobox'));
        await userEvent.click(
          await screen.findByRole('option', { name: 'Yahoo' }),
        );
        await userEvent.type(
          screen.getByPlaceholderText('League ID'),
          leagueId,
        );
        await userEvent.click(
          screen.getByRole('button', { name: /^connect$/i }),
        );
      },
    );

    then('the Yahoo authorization is requested for that league', async () => {
      await vi.waitFor(() => {
        expect(authorizeLeagueId).toBe('45.l.678');
        expect(window.location.href).toBe(
          'https://consent.yahoo.test/authorize?x=1',
        );
      });
    });
  });
});
