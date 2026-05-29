/**
 * Message protocol shared between the page, the content script, and the
 * service worker.
 *
 * NOTE: the page-side mirror of `WINDOW_MSG` and `EspnCookieResult` lives in
 * `frontend/src/lib/espn-extension.ts`. Keep the string values in sync.
 */

/** Window messages exchanged between the LeagueQL page and the content script. */
export const WINDOW_MSG = {
  /** Content script -> page: the extension is installed and listening. */
  ready: 'LEAGUEQL_EXTENSION_READY',
  /** Page -> content script: please fetch the ESPN cookies. */
  request: 'LEAGUEQL_ESPN_COOKIE_REQUEST',
  /** Content script -> page: here are the ESPN cookies (or an error). */
  response: 'LEAGUEQL_ESPN_COOKIE_RESPONSE',
} as const;

/** Runtime messages exchanged between the content script and the service worker. */
export const RUNTIME_MSG = {
  getEspnCookies: 'GET_ESPN_COOKIES',
} as const;

export interface EspnCookieResult {
  ok: boolean;
  swid?: string;
  espnS2?: string;
  error?: 'not_logged_in';
}
