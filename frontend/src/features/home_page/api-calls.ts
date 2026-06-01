import { queryLeague } from '@/components/api/leagues';
import type {
  Platform,
  SeasonStandingsItem,
  MatchupItem,
} from '@/components/api/types';

export function getAllSeasonStandings(
  leagueId: string,
  platform: Platform,
): Promise<{ data: SeasonStandingsItem[] }> {
  return queryLeague<SeasonStandingsItem>(
    leagueId,
    platform,
    'SEASON_STANDINGS#',
  );
}

export function getAllSeasonMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  return queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#');
}
