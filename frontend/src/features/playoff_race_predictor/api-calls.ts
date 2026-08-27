import { queryLeague } from '@/components/api/leagues';
import type {
  LeagueSettingsItem,
  MatchupItem,
  Platform,
} from '@/components/api/types';

export type { LeagueSettingsItem } from '@/components/api/types';

export interface GetMatchupsResponse {
  data: MatchupItem[];
}

export interface GetLeagueSettingsResponse {
  data: LeagueSettingsItem[];
}

export function getMatchups(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetMatchupsResponse> {
  return queryLeague<MatchupItem>(leagueId, platform, `MATCHUPS#${season}#`);
}

export function getLeagueSettings(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetLeagueSettingsResponse> {
  return queryLeague<LeagueSettingsItem>(
    leagueId,
    platform,
    `LEAGUE_SETTINGS#${season}`,
  );
}
