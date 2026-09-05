/**
 * Page-side bridge to the LeagueQL ESPN Cookie Helper Chrome extension.
 *
 * The extension's content script reads the user's ESPN cookies and relays them
 * here over `window.postMessage`. This module never touches `chrome.*` APIs, so
 * the app stays free of extension typings.
 *
 * The message protocol mirrors `extension/src/messages.ts` — keep the string
 * values in sync.
 */

const WINDOW_MSG = {
  ready: 'LEAGUEQL_EXTENSION_READY',
  request: 'LEAGUEQL_ESPN_COOKIE_REQUEST',
  response: 'LEAGUEQL_ESPN_COOKIE_RESPONSE',
} as const;

const EXTENSION_ATTR = 'data-leagueql-espn-extension';
const REQUEST_TIMEOUT_MS = 5000;

/** Chrome Web Store listing for the LeagueQL ESPN Cookie Helper extension. */
export const ESPN_EXTENSION_URL =
  'https://chromewebstore.google.com/detail/leagueql-espn-cookie-help/iinibakcpfopdipfoacabnmcngogbcmg';

interface EspnCookieResponse {
  type: string;
  ok?: boolean;
  swid?: string;
  espnS2?: string;
  error?: 'not_logged_in';
}

export interface EspnCookies {
  swid: string;
  espnS2: string;
}

export type EspnExtensionErrorReason =
  'not_logged_in' | 'timeout' | 'unavailable';

export class EspnExtensionError extends Error {
  readonly reason: EspnExtensionErrorReason;

  constructor(message: string, reason: EspnExtensionErrorReason) {
    super(message);
    this.name = 'EspnExtensionError';
    this.reason = reason;
  }
}

/** Whether the extension's content script has flagged this page. */
export function isEspnExtensionAvailable(): boolean {
  return document.documentElement.getAttribute(EXTENSION_ATTR) === '1';
}

/**
 * Subscribe to the extension's "ready" announcement, which fires if the content
 * script loads after this page has already mounted. Returns an unsubscribe fn.
 */
export function onEspnExtensionReady(callback: () => void): () => void {
  const handler = (event: MessageEvent) => {
    if (event.source !== window) return;
    if ((event.data as { type?: string } | null)?.type === WINDOW_MSG.ready) {
      callback();
    }
  };
  window.addEventListener('message', handler);
  return () => {
    window.removeEventListener('message', handler);
  };
}

/**
 * Ask the extension for the current ESPN cookies. Rejects with an
 * {@link EspnExtensionError} if the user isn't logged into ESPN, the extension
 * is missing, or no response arrives in time.
 */
export function requestEspnCookies(): Promise<EspnCookies> {
  if (!isEspnExtensionAvailable()) {
    return Promise.reject(
      new EspnExtensionError('Extension not installed', 'unavailable'),
    );
  }

  return new Promise<EspnCookies>((resolve, reject) => {
    const cleanup = () => {
      window.removeEventListener('message', handler);
      clearTimeout(timer);
    };

    const timer = setTimeout(() => {
      cleanup();
      reject(new EspnExtensionError('Extension did not respond', 'timeout'));
    }, REQUEST_TIMEOUT_MS);

    const handler = (event: MessageEvent) => {
      if (event.source !== window) return;
      const data = event.data as EspnCookieResponse | null;
      if (data?.type !== WINDOW_MSG.response) return;
      cleanup();
      if (data.ok && data.swid && data.espnS2) {
        resolve({ swid: data.swid, espnS2: data.espnS2 });
      } else {
        reject(new EspnExtensionError('Not logged into ESPN', 'not_logged_in'));
      }
    };

    window.addEventListener('message', handler);
    window.postMessage({ type: WINDOW_MSG.request }, window.location.origin);
  });
}
