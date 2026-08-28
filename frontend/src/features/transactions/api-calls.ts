import { queryLeague } from '@/components/api/leagues';
import type {
  MatchupItem,
  Platform,
  TransactionItem,
} from '@/components/api/types';
import { ApiError } from '@/lib/api-client';

export type {
  TransactionItem,
  TransactionPlayer,
  TransactionTeam,
  TransactionDraftPick,
} from '@/components/api/types';
export type { MatchupItem } from '@/components/api/types';
export { getSeasonMatchups } from '@/features/matchups/api-calls';

/** player_id (string) → week (number) → fantasy points scored that week. */
export type WeeklyPlayerPoints = Map<string, Map<number, number>>;

/**
 * Index a season's matchup box scores as player → week → points.
 *
 * Every player on a roster that week appears in one of the four `PlayerStat[]` arrays
 * (each team's starters + bench), so this covers all rostered players for regular *and*
 * playoff weeks. `PlayerStat.player_id` is a number while `TransactionPlayer.player_id`
 * is a string, so keys are normalised to strings for the join in `rosPointsFor`.
 */
export function buildWeeklyPlayerPoints(
  matchups: MatchupItem[],
): WeeklyPlayerPoints {
  const byPlayer: WeeklyPlayerPoints = new Map();
  for (const m of matchups) {
    const week = Number(m.week);
    const rosters = [
      m.team_a_starters,
      m.team_a_bench,
      m.team_b_starters,
      m.team_b_bench,
    ];
    for (const roster of rosters) {
      for (const p of roster) {
        const id = String(p.player_id);
        let weeks = byPlayer.get(id);
        if (!weeks) {
          weeks = new Map();
          byPlayer.set(id, weeks);
        }
        weeks.set(week, p.points_scored);
      }
    }
  }
  return byPlayer;
}

/**
 * Total fantasy points a player scored from `tradeWeek` onward (inclusive), rounded to 2 dp.
 *
 * There is no explicit upper bound: the matchup box scores only contain weeks that were
 * played, up to the last playoff week, so summing every week `>= tradeWeek` naturally stops
 * at the end of the season. A player absent from the box scores (never rostered in range)
 * contributes 0.
 */
export function rosPointsFor(
  playerId: string,
  tradeWeek: number,
  weekly: WeeklyPlayerPoints,
): number {
  const weeks = weekly.get(playerId);
  if (!weeks) return 0;
  let total = 0;
  for (const [week, points] of weeks) {
    if (week >= tradeWeek) total += points;
  }
  return Math.round(total * 100) / 100;
}

export interface GetTransactionsResponse {
  data: TransactionItem[];
}

/**
 * Fetch a season's transactions (waivers, trades, free agents) for a league.
 *
 * Sleeper-only (backend/sleeper-transactions / frontend/transactions). A season with no completed transactions has no
 * TRANSACTIONS item and 404s; that is a legitimate empty result, so a 404 resolves to an
 * empty list. Any other failure propagates so the page can show an inline error.
 */
export function getTransactions(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetTransactionsResponse> {
  return queryLeague<TransactionItem>(
    leagueId,
    platform,
    `TRANSACTIONS#${season}`,
  ).catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 404) {
      return { data: [] as TransactionItem[] };
    }
    throw err;
  });
}
