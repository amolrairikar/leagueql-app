import { queryLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';

export interface DraftPickItem {
  actual_position_rank: number;
  auto_draft_type_id: number;
  bid_amount: number;
  drafted_position_rank: number;
  draft_rank_delta: number;
  is_auction: boolean;
  keeper: boolean;
  lineup_slot_id: number;
  member_id: string;
  nominating_team_id: number;
  overall_pick_number: number;
  owner_username: string;
  pick_id: number;
  player_id: string;
  player_name: string;
  position: string;
  reserved_for_keeper: boolean;
  round: number;
  round_pick_number: number;
  season: string;
  team_id: string;
  team_logo: string;
  team_name: string;
  total_points: number;
  trade_locked: boolean;
  vorp: number | null;
}

export function getDraftData(
  leagueId: string,
  platform: Platform,
  season: string,
  auction = false,
): Promise<{ data: DraftPickItem[] }> {
  // `auction` selects the demo-only DRAFT_AUCTION dataset; in production this is
  // always false and the standard DRAFT query is used.
  const queryType = auction ? `DRAFT_AUCTION#${season}` : `DRAFT#${season}`;
  return queryLeague<DraftPickItem>(leagueId, platform, queryType);
}
