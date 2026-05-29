import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  isEspnExtensionAvailable,
  requestEspnCookies,
} from '../espn-extension';

const ATTR = 'data-leagueql-espn-extension';
const RESPONSE = 'LEAGUEQL_ESPN_COOKIE_RESPONSE';

function setInstalled(installed: boolean): void {
  if (installed) {
    document.documentElement.setAttribute(ATTR, '1');
  } else {
    document.documentElement.removeAttribute(ATTR);
  }
}

// Simulate the content script's reply. jsdom's window.postMessage does not set
// `event.source`, so dispatch the MessageEvent directly with source = window to
// satisfy the helper's same-window guard.
function postFromContentScript(data: Record<string, unknown>): void {
  window.dispatchEvent(new MessageEvent('message', { data, source: window }));
}

describe('isEspnExtensionAvailable', () => {
  afterEach(() => {
    setInstalled(false);
  });

  it('reflects the content-script flag', () => {
    expect(isEspnExtensionAvailable()).toBe(false);
    setInstalled(true);
    expect(isEspnExtensionAvailable()).toBe(true);
  });
});

describe('requestEspnCookies', () => {
  afterEach(() => {
    setInstalled(false);
    vi.useRealTimers();
  });

  it('rejects when the extension is not installed', async () => {
    setInstalled(false);
    await expect(requestEspnCookies()).rejects.toMatchObject({
      reason: 'unavailable',
    });
  });

  it('resolves with cookies on an ok response', async () => {
    setInstalled(true);
    const promise = requestEspnCookies();
    postFromContentScript({
      type: RESPONSE,
      ok: true,
      swid: '{abc}',
      espnS2: 's2val',
    });
    await expect(promise).resolves.toEqual({ swid: '{abc}', espnS2: 's2val' });
  });

  it('rejects with not_logged_in on a failed response', async () => {
    setInstalled(true);
    const promise = requestEspnCookies();
    postFromContentScript({
      type: RESPONSE,
      ok: false,
      error: 'not_logged_in',
    });
    await expect(promise).rejects.toMatchObject({ reason: 'not_logged_in' });
  });

  it('rejects with timeout when no response arrives', async () => {
    vi.useFakeTimers();
    setInstalled(true);
    const promise = requestEspnCookies();
    const expectation = expect(promise).rejects.toMatchObject({
      reason: 'timeout',
    });
    await vi.advanceTimersByTimeAsync(5000);
    await expectation;
  });
});
