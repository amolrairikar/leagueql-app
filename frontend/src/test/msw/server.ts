/**
 * Mock Service Worker server for component tests.
 *
 * MSW intercepts `fetch`, so the real `apiClient` (cache, dedup, bearer-token
 * attach, `ApiError` mapping) and the `toResult`/`<ErrorAlert>` path all run —
 * the component boundary we want. Helpers below build the common LeagueQL
 * response shapes for the three UI states (loads-fine / data-error / empty).
 */
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';

export const API = 'http://test.local';

export const server = setupServer();

/** A `GET /leagues/:id` (metadata) handler returning the standard envelope. */
export function leagueMetadata(data: {
  seasons?: string[];
  league_name?: string | null;
  is_owner?: boolean;
}) {
  return http.get(`${API}/leagues/:id`, () =>
    HttpResponse.json({
      detail: 'Found league',
      data: {
        seasons: data.seasons ?? [],
        league_name: data.league_name ?? null,
        is_owner: data.is_owner ?? false,
      },
    }),
  );
}

/** A `GET /leagues/:id` handler that fails with a status (e.g. 403 for ESPN non-members). */
export function leagueMetadataError(status = 403) {
  return http.get(`${API}/leagues/:id`, () =>
    HttpResponse.json({ detail: 'Not a member of this league' }, { status }),
  );
}

/**
 * A `GET /leagues/:id/query` handler keyed by the `queryType` param.
 *
 * `rows` maps a queryType base (e.g. `SEASON_STANDINGS`, `MATCHUPS`) to the row
 * array to return. An unmapped queryType resolves to 404 (the real backend's
 * "no data" response), which also models `getMigrationMapping`'s tolerated 404.
 */
export function leagueQuery(rows: Record<string, unknown[]>) {
  return http.get(`${API}/leagues/:id/query`, ({ request }) => {
    const queryType = new URL(request.url).searchParams.get('queryType') ?? '';
    const base = queryType.split('#')[0].toUpperCase();
    const data = rows[base];
    if (data === undefined) {
      return HttpResponse.json(
        { detail: 'No data found for the requested query' },
        { status: 404 },
      );
    }
    return HttpResponse.json({ data });
  });
}

/** A handler that fails every league query with a 500 (data-load-error state). */
export function leagueQueryError(status = 500) {
  return http.get(`${API}/leagues/:id/query`, () =>
    HttpResponse.json({ detail: 'Internal Server Error' }, { status }),
  );
}

/** A `POST` handler returning a JSON body with a status code. */
export function postJson(path: string, body: JsonBodyType, status = 200) {
  return http.post(`${API}${path}`, () => HttpResponse.json(body, { status }));
}
