import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RUNTIME_MSG } from '../messages';

type Listener = (
  message: unknown,
  sender: unknown,
  sendResponse: (r: unknown) => void,
) => boolean | undefined;

let listener: Listener;
let cookiesGet: ReturnType<typeof vi.fn>;

function cookieStore(values: Record<string, string | undefined>) {
  cookiesGet.mockImplementation(async ({ name }: { name: string }) =>
    values[name] === undefined ? null : { value: values[name] },
  );
}

/** Invoke the registered listener and resolve with whatever it sends back. */
function dispatch(message: unknown): Promise<unknown> {
  return new Promise((resolve) => {
    const keepOpen = listener(message, {}, resolve);
    if (keepOpen === undefined) resolve('no-response');
  });
}

beforeEach(async () => {
  vi.resetModules();
  cookiesGet = vi.fn();
  vi.stubGlobal('chrome', {
    cookies: { get: cookiesGet },
    runtime: {
      onMessage: {
        addListener: vi.fn((l: Listener) => {
          listener = l;
        }),
      },
    },
  });
  await import('../background');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('background service worker', () => {
  it('registers exactly one onMessage listener', () => {
    expect(chrome.runtime.onMessage.addListener).toHaveBeenCalledTimes(1);
  });

  it('returns both cookies, with SWID kept raw (braces included)', async () => {
    cookieStore({ SWID: '{ABC-123}', espn_s2: 's2-value' });
    const result = await dispatch({ type: RUNTIME_MSG.getEspnCookies });
    expect(result).toEqual({ ok: true, swid: '{ABC-123}', espnS2: 's2-value' });
  });

  it('looks cookies up on the ESPN domain', async () => {
    cookieStore({ SWID: '{A}', espn_s2: 'x' });
    await dispatch({ type: RUNTIME_MSG.getEspnCookies });
    expect(cookiesGet).toHaveBeenCalledWith({
      url: 'https://fantasy.espn.com',
      name: 'SWID',
    });
    expect(cookiesGet).toHaveBeenCalledWith({
      url: 'https://fantasy.espn.com',
      name: 'espn_s2',
    });
  });

  it('keeps the message channel open (returns true) for async replies', () => {
    cookieStore({ SWID: '{A}', espn_s2: 'x' });
    expect(listener({ type: RUNTIME_MSG.getEspnCookies }, {}, vi.fn())).toBe(
      true,
    );
  });

  it.each([
    ['SWID missing', { espn_s2: 'x' }],
    ['espn_s2 missing', { SWID: '{A}' }],
    ['both missing', {}],
    ['SWID empty', { SWID: '', espn_s2: 'x' }],
    ['espn_s2 empty', { SWID: '{A}', espn_s2: '' }],
  ])('reports not_logged_in when %s', async (_label, values) => {
    cookieStore(values);
    const result = await dispatch({ type: RUNTIME_MSG.getEspnCookies });
    expect(result).toEqual({ ok: false, error: 'not_logged_in' });
  });

  it('reports not_logged_in when the cookies API rejects', async () => {
    cookiesGet.mockRejectedValue(new Error('boom'));
    const result = await dispatch({ type: RUNTIME_MSG.getEspnCookies });
    expect(result).toEqual({ ok: false, error: 'not_logged_in' });
  });

  it.each([
    ['an unknown type', { type: 'SOMETHING_ELSE' }],
    ['no type', {}],
    ['null', null],
    ['undefined', undefined],
  ])('ignores %s messages without responding', async (_label, message) => {
    const sendResponse = vi.fn();
    expect(listener(message, {}, sendResponse)).toBeUndefined();
    expect(sendResponse).not.toHaveBeenCalled();
    expect(cookiesGet).not.toHaveBeenCalled();
  });
});
