/**
 * Demo-mode API shim.
 *
 * When the app is running in demo mode, no real backend requests are made.
 * All data is served from the pre-generated demo-data.json, which is produced
 * deterministically by scripts/utility_scripts/seed_demo_data.py (seed=42).
 *
 * Query resolution mirrors the DynamoDB SK logic in src/api/main.py:
 *   - queryType with a trailing "#" (or no "#" suffix at all) → begins_with scan
 *   - queryType with a non-empty suffix after the first "#"   → exact key lookup
 */

import { DEMO_SEASONS } from './demo-constants';

import type { GetLeagueResponse } from '@/components/api/types';

// ── SK-base mapping (mirrors QUERY_TYPE_TO_SK_BASE in main.py) ────────────────

const QUERY_TYPE_TO_SK_BASE: Record<string, string> = {
  TEAMS: 'TEAMS',
  MATCHUPS: 'MATCHUPS',
  SEASON_STANDINGS: 'STANDINGS',
  WEEKLY_STANDINGS: 'WEEKLY_STANDINGS',
  PLAYOFF_BRACKET: 'PLAYOFF_BRACKET',
  DRAFT: 'DRAFT',
  // Demo-only: a separate auction-format draft dataset, selected by the draft
  // recap's demo toggle. Has no counterpart in the real backend QueryType.
  DRAFT_AUCTION: 'DRAFT_AUCTION',
  PLATFORM_MIGRATION: 'PLATFORM_MIGRATION',
};

// ── Module-level cache (loaded once per session) ───────────────────────────────

let _data: Record<string, unknown[]> | null = null;
let _leagueName = 'Demo Fantasy League';

async function loadDemoData(): Promise<Record<string, unknown[]>> {
  if (_data) return _data;
  const json = await import('./demo-data.json');
  const payload = json.default as {
    league_name: string;
    data: Record<string, unknown[]>;
  };
  _leagueName = payload.league_name;
  _data = payload.data;
  return _data;
}

// ── SK resolution (mirrors query_league in main.py) ───────────────────────────

function resolveQuery(
  data: Record<string, unknown[]>,
  queryType: string,
): unknown[] {
  const firstHash = queryType.indexOf('#');
  const baseType = firstHash >= 0 ? queryType.slice(0, firstHash) : queryType;
  const suffix = firstHash >= 0 ? queryType.slice(firstHash + 1) : null;

  const skBase = QUERY_TYPE_TO_SK_BASE[baseType.toUpperCase()];
  if (!skBase) return [];

  // Matches Python: sk = f"{sk_base}#{suffix}" if suffix is not None else f"{sk_base}#"
  const sk = suffix !== null ? `${skBase}#${suffix}` : `${skBase}#`;

  if (sk.endsWith('#')) {
    // begins_with → collect and flatten all matching items
    return Object.entries(data)
      .filter(([key]) => key.startsWith(sk))
      .flatMap(([, items]) => items);
  }

  // exact match
  return data[sk] ?? [];
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Resolves a queryType string against the demo dataset.
 * Returns the same shape as the real `/leagues/{id}/query` endpoint: `{ data: T[] }`.
 */
export async function queryDemoLeague<T = unknown>(
  queryType: string,
): Promise<{ data: T[] }> {
  const data = await loadDemoData();
  return { data: resolveQuery(data, queryType) as T[] };
}

/**
 * Returns the demo league metadata (seasons, name).
 * Mirrors the real `GET /leagues/{leagueId}` response.
 */
export async function getDemoLeague(): Promise<GetLeagueResponse> {
  await loadDemoData();
  return {
    detail: 'Found league',
    data: {
      seasons: DEMO_SEASONS,
      league_name: _leagueName,
      // The demo viewer is treated as the owner of the sample league. Demo mode
      // bypasses owner/membership gating anyway; this keeps the response shape
      // faithful to the real endpoint (LQL-01 / BE-016).
      is_owner: true,
    },
  };
}
