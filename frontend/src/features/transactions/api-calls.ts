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
 * `untilWeek` is an optional exclusive upper bound (e.g. the week an added player was later
 * dropped). Without it, the sum runs to the end of the season: the matchup box scores only
 * contain weeks that were played, up to the last playoff week. A player absent from the box
 * scores (never rostered in range) contributes 0.
 */
export function rosPointsFor(
  playerId: string,
  tradeWeek: number,
  weekly: WeeklyPlayerPoints,
  untilWeek = Infinity,
): number {
  const weeks = weekly.get(playerId);
  if (!weeks) return 0;
  let total = 0;
  for (const [week, points] of weeks) {
    if (week >= tradeWeek && week < untilWeek) total += points;
  }
  return Math.round(total * 100) / 100;
}

/** `${roster_id}:${player_id}` → week → points scored while in that roster's starters or bench. */
export type RosterWeeklyPoints = Map<string, Map<number, number>>;

/**
 * Index a season's matchup box scores as roster+player → week → points, so a player's points can be
 * limited to weeks they were actually in a given roster's lineup. Unlike `buildWeeklyPlayerPoints`
 * it keeps the team: each matchup's `team_a_*` lists are filed under `team_a_id` and `team_b_*`
 * under `team_b_id` (the same ids a transaction's `roster_id` uses on every platform), stringified
 * for the join.
 */
export function buildRosterWeeklyPoints(
  matchups: MatchupItem[],
): RosterWeeklyPoints {
  const byRosterPlayer: RosterWeeklyPoints = new Map();
  for (const m of matchups) {
    const week = Number(m.week);
    const lineups: [string, MatchupItem['team_a_starters'][]][] = [
      [String(m.team_a_id), [m.team_a_starters, m.team_a_bench]],
      [String(m.team_b_id), [m.team_b_starters, m.team_b_bench]],
    ];
    for (const [rosterId, lists] of lineups) {
      for (const list of lists) {
        for (const p of list) {
          const key = `${rosterId}:${p.player_id}`;
          let weeks = byRosterPlayer.get(key);
          if (!weeks) {
            weeks = new Map();
            byRosterPlayer.set(key, weeks);
          }
          weeks.set(week, p.points_scored);
        }
      }
    }
  }
  return byRosterPlayer;
}

/**
 * Total points a player scored for `rosterId` from `fromWeek` (inclusive) up to `untilWeek`
 * (exclusive), counting only weeks they appear in that roster's starters or bench. Rounded to 2 dp.
 */
export function rosterPointsFor(
  rosterId: string,
  playerId: string,
  fromWeek: number,
  rosterWeekly: RosterWeeklyPoints,
  untilWeek = Infinity,
): number {
  const weeks = rosterWeekly.get(`${rosterId}:${playerId}`);
  if (!weeks) return 0;
  let total = 0;
  for (const [week, points] of weeks) {
    if (week >= fromWeek && week < untilWeek) total += points;
  }
  return Math.round(total * 100) / 100;
}

export interface GetTransactionsResponse {
  data: TransactionItem[];
}

/**
 * Fetch a season's transactions (waivers, trades, free agents) for a league.
 *
 * Works for both Sleeper (all seasons) and ESPN (current season only) leagues
 * (backend/sleeper-transactions, backend/espn-transactions, frontend/transactions). A season with no
 * transactions has no TRANSACTIONS item and 404s; that is a legitimate empty result, so a 404
 * resolves to an empty list. Any other failure propagates so the page can show an inline error.
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
