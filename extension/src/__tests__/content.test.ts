import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RUNTIME_MSG, WINDOW_MSG } from '../messages';

type SendCallback = (result: unknown) => void;

let sendMessage: ReturnType<typeof vi.fn>;
let lastError: { message: string } | undefined;
let received: Array<Record<string, unknown>>;
let collector: (e: MessageEvent) => void;
let contentListeners: EventListener[];

/**
 * Simulate the page posting to itself. jsdom's postMessage delivers events with
 * `source: null` (a real browser sets `source` to the sender window), so dispatch
 * the event directly with `source: window`, which is what the content script trusts.
 */
async function pageSends(data: unknown) {
  window.dispatchEvent(new MessageEvent('message', { data, source: window }));
  await new Promise((r) => setTimeout(r, 10));
}

beforeEach(async () => {
  vi.resetModules();
  document.documentElement.removeAttribute('data-leagueql-espn-extension');
  lastError = undefined;
  received = [];
  sendMessage = vi.fn();
  vi.stubGlobal('chrome', {
    runtime: {
      sendMessage,
      get lastError() {
        return lastError;
      },
    },
  });
  collector = (e) => {
    if (e.data && typeof e.data === 'object') received.push(e.data);
  };
  window.addEventListener('message', collector);
  // The script registers a window listener on import; capture it so it can be
  // removed afterwards (re-importing per test would otherwise stack listeners).
  contentListeners = [];
  const realAdd = window.addEventListener.bind(window);
  const addSpy = vi
    .spyOn(window, 'addEventListener')
    .mockImplementation(
      (type: string, l: EventListenerOrEventListenerObject) => {
        if (type === 'message') contentListeners.push(l as EventListener);
        realAdd(type, l);
      },
    );
  await import('../content');
  addSpy.mockRestore();
  await new Promise((r) => setTimeout(r, 10));
});

afterEach(() => {
  window.removeEventListener('message', collector);
  contentListeners.forEach((l) => window.removeEventListener('message', l));
  vi.unstubAllGlobals();
});

const responses = () => received.filter((m) => m.type === WINDOW_MSG.response);

describe('content script', () => {
  it('flags the document so the page can detect the extension on mount', () => {
    expect(
      document.documentElement.getAttribute('data-leagueql-espn-extension'),
    ).toBe('1');
  });

  it('announces readiness to the page', () => {
    expect(received).toContainEqual({ type: WINDOW_MSG.ready });
  });

  it('forwards a page request to the service worker and relays the cookies', async () => {
    sendMessage.mockImplementation((_msg: unknown, cb: SendCallback) =>
      cb({ ok: true, swid: '{A}', espnS2: 'tok' }),
    );
    await pageSends({ type: WINDOW_MSG.request });
    expect(sendMessage).toHaveBeenCalledWith(
      { type: RUNTIME_MSG.getEspnCookies },
      expect.any(Function),
    );
    expect(responses()).toEqual([
      { type: WINDOW_MSG.response, ok: true, swid: '{A}', espnS2: 'tok' },
    ]);
  });

  it('relays a not_logged_in result from the service worker', async () => {
    sendMessage.mockImplementation((_msg: unknown, cb: SendCallback) =>
      cb({ ok: false, error: 'not_logged_in' }),
    );
    await pageSends({ type: WINDOW_MSG.request });
    expect(responses()).toEqual([
      { type: WINDOW_MSG.response, ok: false, error: 'not_logged_in' },
    ]);
  });

  it('degrades to not_logged_in when chrome.runtime.lastError is set', async () => {
    sendMessage.mockImplementation((_msg: unknown, cb: SendCallback) => {
      lastError = { message: 'Extension context invalidated' };
      cb({ ok: true, swid: '{A}', espnS2: 'tok' });
    });
    await pageSends({ type: WINDOW_MSG.request });
    expect(responses()).toEqual([
      { type: WINDOW_MSG.response, ok: false, error: 'not_logged_in' },
    ]);
  });

  it('degrades to not_logged_in when the service worker returns nothing', async () => {
    sendMessage.mockImplementation((_msg: unknown, cb: SendCallback) =>
      cb(undefined),
    );
    await pageSends({ type: WINDOW_MSG.request });
    expect(responses()).toEqual([
      { type: WINDOW_MSG.response, ok: false, error: 'not_logged_in' },
    ]);
  });

  it.each([
    ['an unrelated type', { type: 'OTHER' }],
    ['a response-type echo', { type: WINDOW_MSG.response }],
    ['a payload with no type', { foo: 'bar' }],
    ['a string payload', 'hello'],
    ['null', null],
  ])('ignores %s', async (_label, data) => {
    await pageSends(data);
    expect(sendMessage).not.toHaveBeenCalled();
  });

  it('ignores request messages that do not originate from this window', () => {
    window.dispatchEvent(
      new MessageEvent('message', {
        data: { type: WINDOW_MSG.request },
        source: null,
      }),
    );
    expect(sendMessage).not.toHaveBeenCalled();
  });
});
