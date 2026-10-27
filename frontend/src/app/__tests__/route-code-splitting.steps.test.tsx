import { act, render, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';

import App from '../app';

import { setClerkState } from '@/test/clerk-mock';
import { server } from '@/test/msw/server';
import { setDemoMode, setLeagueCookie } from '@/test/render';

// Page modules are mocked so each lazy import can be held open, rejected, or counted.
const mocks = vi.hoisted(() => {
  const deferred = () => {
    let resolve!: () => void;
    const promise = new Promise<void>((r) => {
      resolve = r;
    });
    return { promise, resolve };
  };
  return {
    home: deferred(),
    docs: deferred(),
    requested: new Set<string>(),
    holdHome: false,
    holdDocs: false,
    failStandings: false,
  };
});

vi.mock('@/features/home_page/home-page', async () => {
  mocks.requested.add('home');
  if (mocks.holdHome) await mocks.home.promise;
  return { default: () => <div>Home page loaded</div> };
});

vi.mock('@/features/instructions/instructions-page', async () => {
  if (mocks.holdDocs) await mocks.docs.promise;
  return { default: () => <div>Docs page loaded</div> };
});

vi.mock('@/features/season_standings/season-standings', () => {
  mocks.requested.add('standings');
  if (mocks.failStandings) throw new Error('Failed to fetch dynamically');
  return { default: () => <div>Standings page loaded</div> };
});

const feature = loadFeature('src/app/__tests__/route-code-splitting.feature');

async function openRoute(path: string) {
  window.history.pushState({}, '', path);
  await act(async () => {
    render(<App />);
    await Promise.resolve();
  });
}

async function navigateTo(path: string) {
  await act(async () => {
    window.history.pushState({}, '', path);
    window.dispatchEvent(new PopStateEvent('popstate'));
    await Promise.resolve();
  });
}

function signedOut() {
  setClerkState({ isLoaded: true, isSignedIn: false, user: null });
  server.use(
    http.get('https://api.leagueql.com/counts', () =>
      HttpResponse.json({ leagueCount: 3 }),
    ),
  );
}

function demoMode() {
  setClerkState({ isLoaded: true, isSignedIn: false, user: null });
  setDemoMode();
  setLeagueCookie('888888888', 'SLEEPER', ['2024']);
}

defineFeature(feature, (test) => {
  test('The landing page does not load league pages', ({
    given,
    when,
    then,
  }) => {
    given('the user is signed out', signedOut);
    when('the app opens the landing page', async () => {
      await openRoute('/');
    });
    then('the standings and home page code is not requested', async () => {
      expect(
        (await screen.findAllByText(/Connect Your League|LeagueQL/i)).length,
      ).toBeGreaterThan(0);
      expect(mocks.requested.has('home')).toBe(false);
      expect(mocks.requested.has('standings')).toBe(false);
    });
  });

  test('An in-app page shows a spinner while keeping the app chrome', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the user is in demo mode', demoMode);
    and('the home page code is still loading', () => {
      mocks.holdHome = true;
    });
    when('the app opens the home page', async () => {
      await openRoute('/home');
    });
    then('I see the loading spinner and the demo banner', async () => {
      expect(
        await screen.findByRole('status', { name: 'Loading' }),
      ).toBeVisible();
      expect(screen.getByText(/Demo Mode/i)).toBeInTheDocument();
    });
    when('the home page code finishes loading', async () => {
      await act(async () => {
        mocks.home.resolve();
        await Promise.resolve();
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A public page shows a spinner while loading', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the user is signed out', signedOut);
    and('the docs page code is still loading', () => {
      mocks.holdDocs = true;
    });
    when('the app opens the docs page', async () => {
      await openRoute('/docs');
    });
    then('I see the loading spinner', async () => {
      expect(
        await screen.findByRole('status', { name: 'Loading' }),
      ).toBeVisible();
    });
    when('the docs page code finishes loading', async () => {
      await act(async () => {
        mocks.docs.resolve();
        await Promise.resolve();
      });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('A failed page load shows the error fallback', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the user is in demo mode', demoMode);
    and('the standings page code fails to load', () => {
      mocks.failStandings = true;
    });
    when('the app opens the standings page', async () => {
      await openRoute('/standings');
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('Navigating away from a failed page recovers', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the user is in demo mode', demoMode);
    and('the standings page code fails to load', () => {
      mocks.failStandings = true;
    });
    when('the app opens the standings page', async () => {
      await openRoute('/standings');
    });
    and('the user navigates to the home page', async () => {
      await navigateTo('/home');
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
