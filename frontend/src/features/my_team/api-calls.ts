/**
 * Data fetching for the My Team report card (frontend/my-team).
 *
 * Assembles a season's precomputed views for the page in one call, reusing the
 * existing per-feature fetchers. Standings and matchups are required; draft and
 * transactions degrade to empty (draft may be absent; transactions are Sleeper-only
 * and already 404-safe), so the page can still render every other section.
 */
import type {
  MatchupItem,
  Platform,
  SeasonStandingsItem,
  TransactionItem,
} from '@/components/api/types';
import {
  type DraftPickItem,
  getDraftData,
} from '@/features/draft_grades/api-calls';
import { getSeasonMatchups } from '@/features/matchups/api-calls';
import { getSeasonStandings } from '@/features/season_standings/api-calls';
import {
  type WeeklyPlayerPoints,
  buildWeeklyPlayerPoints,
  getTransactions,
} from '@/features/transactions/api-calls';

export interface MyTeamData {
  standings: SeasonStandingsItem[];
  matchups: MatchupItem[];
  draftPicks: DraftPickItem[];
  transactions: TransactionItem[];
  weekly: WeeklyPlayerPoints;
}

/**
 * Fetch everything the report card needs for a season. Rejects only when a required
 * view (standings, matchups) fails; draft and transactions failures degrade to `[]`.
 */
export async function getMyTeamData(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<MyTeamData> {
  const [standings, matchups, draftPicks] = await Promise.all([
    getSeasonStandings(leagueId, platform, season).then((r) => r.data),
    getSeasonMatchups(leagueId, platform, season).then((r) => r.data),
    getDraftData(leagueId, platform, season)
      .then((r) => r.data)
      .catch(() => [] as DraftPickItem[]),
  ]);

  const transactions =
    platform === 'SLEEPER'
      ? await getTransactions(leagueId, platform, season)
          .then((r) => r.data)
          .catch(() => [] as TransactionItem[])
      : [];

  return {
    standings,
    matchups,
    draftPicks,
    transactions,
    weekly: buildWeeklyPlayerPoints(matchups),
  };
}
