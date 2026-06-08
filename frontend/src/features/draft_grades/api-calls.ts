import { queryLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';

export interface DraftPickItem {
  // Scoring-derived fields (actual_position_rank, draft_rank_delta, total_points,
  // vorp) are null for picks with no end-of-season scoring row — e.g. Sleeper
  // D/ST and kickers, or players who never recorded stats. They all come from
  // the same LEFT JOIN, so they go null together.
  actual_position_rank: number | null;
  auto_draft_type_id: number;
  bid_amount: number;
  drafted_position_rank: number;
  draft_rank_delta: number | null;
  is_auction: boolean;
  keeper: boolean;
  lineup_slot_id: number;
  member_id: string;
  nominating_team_id: number;
  overall_pick_number: number;
  owner_username: string;
  pick_id: number;
  player_id: string;
  player_name: string | null;
  position: string;
  reserved_for_keeper: boolean;
  round: number;
  round_pick_number: number;
  season: string;
  team_id: string;
  team_logo: string;
  team_name: string;
  total_points: number | null;
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
