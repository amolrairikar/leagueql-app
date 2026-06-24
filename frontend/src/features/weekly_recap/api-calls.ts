import { queryLeague } from '@/components/api/leagues';
import type { MatchupItem, Platform } from '@/components/api/types';
import { ApiError } from '@/lib/api-client';

/** One cached AI weekly matchup recap (BE-022 / FE-037). */
export interface RecapItem {
  headline: string;
  body: string;
  generated_at: string;
}

/**
 * Regular-season + playoff matchups for one season, used only to resolve the
 * latest available week when no week is explicitly selected (mirrors how the
 * Weekly Awards section defaults the active week). The underlying query is cached,
 * so this shares the Matchups page's existing fetch rather than adding a round-trip.
 */
export function getSeasonMatchups(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<{ data: MatchupItem[] }> {
  return queryLeague<MatchupItem>(leagueId, platform, `MATCHUPS#${season}#`);
}

/**
 * Fetch the cached recap for a single week.
 *
 * A week with no recap yet legitimately 404s (the item only exists once the
 * recap-generator Lambda has run for that week); that is surfaced as an empty
 * `data` list so the component renders its empty state rather than an error.
 * Any other failure (5xx / network) propagates so it surfaces as an inline error.
 */
export async function getWeekRecap(
  leagueId: string,
  platform: Platform,
  season: string,
  week: number,
): Promise<{ data: RecapItem[] }> {
  const week2 = String(week).padStart(2, '0');
  try {
    return await queryLeague<RecapItem>(
      leagueId,
      platform,
      `MATCHUP_RECAP#${season}#WEEK#${week2}`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return { data: [] };
    }
    throw err;
  }
}
