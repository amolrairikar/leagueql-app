import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { RUNTIME_MSG, WINDOW_MSG } from '../messages';

describe('message protocol', () => {
  it('keeps stable wire values', () => {
    expect(WINDOW_MSG).toEqual({
      ready: 'LEAGUEQL_EXTENSION_READY',
      request: 'LEAGUEQL_ESPN_COOKIE_REQUEST',
      response: 'LEAGUEQL_ESPN_COOKIE_RESPONSE',
    });
    expect(RUNTIME_MSG).toEqual({ getEspnCookies: 'GET_ESPN_COOKIES' });
  });

  // The page-side mirror lives in the frontend; a drift here silently breaks autofill.
  it('matches the frontend mirror in frontend/src/lib/espn-extension.ts', () => {
    const mirror = readFileSync(
      resolve(__dirname, '../../../frontend/src/lib/espn-extension.ts'),
      'utf8',
    );
    for (const value of Object.values(WINDOW_MSG)) {
      expect(mirror).toContain(value);
    }
  });
});
