/**
 * Global Vitest setup for component tests (wired via vite.config `setupFiles`).
 *
 * - registers `@testing-library/jest-dom` matchers
 * - mocks `@clerk/react` (no live key/network in tests)
 * - polyfills the jsdom gaps recharts / the sidebar rely on
 * - starts the MSW server and resets handlers, cookies, and the API cache per test
 */
import '@testing-library/jest-dom/vitest';

import { configure } from '@testing-library/dom';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

import { server } from './msw/server';

import { clearApiCache } from '@/lib/api-client';
import { setFlagsForTesting } from '@/lib/feature-flags';

// The default `findBy*` async timeout (1000ms) is too tight for a loaded CI
// runner: async data load + render (e.g. the home dashboard's headline stats)
// occasionally exceeds it there while passing locally, causing flaky
// "Unable to find element" failures. Raise it globally for all component tests.
configure({ asyncUtilTimeout: 5000 });

vi.mock('@clerk/react', () => import('./clerk-mock'));

// recharts (home/standings charts) needs ResizeObserver; jsdom lacks it.
class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverStub;

// The docs page's scroll-spy uses IntersectionObserver; jsdom lacks it.
class IntersectionObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);
  root = null;
  rootMargin = '';
  thresholds = [];
}
globalThis.IntersectionObserver =
  globalThis.IntersectionObserver ?? IntersectionObserverStub;

// Radix UI primitives (Select, etc.) call pointer-capture + scrollIntoView APIs
// that jsdom doesn't implement; stub them so dropdowns are drivable in tests.
const proto = window.Element.prototype as unknown as Record<string, unknown>;
proto.hasPointerCapture ??= vi.fn();
proto.setPointerCapture ??= vi.fn();
proto.releasePointerCapture ??= vi.fn();
proto.scrollIntoView ??= vi.fn();

// Newer Node ships an experimental built-in `localStorage` that shadows jsdom's
// proper Web Storage implementation: on some versions it's a plain object with no
// Storage methods, and on others (Node 25+, without `--localstorage-file`) it's
// disabled entirely so `window.localStorage` is `undefined`. Guard against both —
// use optional chaining so a missing `localStorage` doesn't throw — and polyfill a
// spec-compliant Storage so production code using window.localStorage works.
if (typeof window.localStorage?.getItem !== 'function') {
  const store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.get(key) ?? null;
    },
    key(index: number) {
      return [...store.keys()][index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  };
  Object.defineProperty(window, 'localStorage', { value: storage });
  Object.defineProperty(globalThis, 'localStorage', { value: storage });
}

// The sidebar / theme read matchMedia; jsdom doesn't implement it.
if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset every feature flag to OFF before each test (the app's fail-safe default).
// Tests that need a flag ON opt in within the test via setFlagsForTesting.
beforeEach(() => setFlagsForTesting({}));

afterEach(async () => {
  server.resetHandlers();
  clearApiCache();
  // Clear all cookies set during the test so demo state never leaks.
  for (const cookie of document.cookie.split(';')) {
    const name = cookie.split('=')[0].trim();
    if (name) document.cookie = `${name}=; path=/; max-age=0`;
  }
  // Clear localStorage league state between tests.
  window.localStorage.clear();
  const { resetClerkState } = await import('./clerk-mock');
  resetClerkState();
});

afterAll(() => server.close());
