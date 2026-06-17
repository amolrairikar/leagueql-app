/**
 * Shared render helper for component tests.
 *
 * Renders a feature under a `MemoryRouter` + `TooltipProvider`, with helpers to
 * set the league/demo cookies that drive `getLeagueCookies()` / `isDemoMode()`.
 * Clerk is mocked globally (see `src/test/setup.ts`); flip auth via
 * `setClerkState` from `./clerk-mock`.
 */
import { act, render } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';
import type { Platform } from '@/lib/cookie-handler';

export interface RenderOptions {
  route?: string;
  league?: { leagueId: string; platform: Platform; seasons: string[] };
  demo?: boolean;
}

export function setLeagueCookie(
  leagueId: string,
  platform: Platform,
  seasons: string[],
) {
  window.localStorage.setItem('leagueId', leagueId);
  window.localStorage.setItem('leaguePlatform', platform);
  window.localStorage.setItem('leagueSeasons', JSON.stringify(seasons));
}

export function setDemoMode() {
  document.cookie = 'demo_mode=true; path=/';
}

// Async + `act`-wrapped: React 19's `use(promise)` only re-renders a Suspense
// boundary on resolution inside an act scope, which jsdom + Vitest does not
// flush via `waitFor` alone — so the render itself runs in `act`.
export async function renderRoute(ui: ReactNode, options: RenderOptions = {}) {
  const { route = '/', league, demo } = options;
  if (league) setLeagueCookie(league.leagueId, league.platform, league.seasons);
  if (demo) setDemoMode();
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <MemoryRouter initialEntries={[route]}>
        <TooltipProvider>{ui as ReactElement}</TooltipProvider>
      </MemoryRouter>,
    );
    // Yield so React 19 flushes Suspense boundaries resolved by `use(promise)`.
    await Promise.resolve();
  });
  return result;
}
