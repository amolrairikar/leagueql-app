import { act, render, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';

import App from '../app';

import { setClerkState } from '@/test/clerk-mock';
import { server } from '@/test/msw/server';
import { setDemoMode, setLeagueCookie } from '@/test/render';

const feature = loadFeature('src/app/__tests__/authentication.feature');

async function openProtectedRoute() {
  window.history.pushState({}, '', '/home');
  await act(async () => {
    render(<App />);
    await Promise.resolve();
  });
}

defineFeature(feature, (test) => {
  test('A signed-out user is redirected away from a protected route', ({
    given,
    when,
    then,
  }) => {
    given('the user is signed out', () => {
      setClerkState({ isLoaded: true, isSignedIn: false, user: null });
      server.use(
        http.get('https://api.leagueql.com/counts', () =>
          HttpResponse.json({ leagueCount: 3 }),
        ),
      );
    });
    when('the app opens a protected route', async () => {
      await openProtectedRoute();
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('Demo mode bypasses authentication', ({ given, when, then }) => {
    given('the user is signed out but demo mode is active', () => {
      setClerkState({ isLoaded: true, isSignedIn: false, user: null });
      setDemoMode();
      // Demo league cookie so the dashboard resolves against local fixtures.
      setLeagueCookie('888888888', 'SLEEPER', ['2024']);
    });
    when('the app opens a protected route', async () => {
      await openProtectedRoute();
    });
    then('I see the demo banner', async () => {
      expect(await screen.findByText(/Demo Mode/i)).toBeInTheDocument();
    });
  });
});
