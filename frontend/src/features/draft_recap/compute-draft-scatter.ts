import type { DraftPickItem } from '@/features/draft_grades/api-calls';
import { FANTASY_POSITION_ORDER } from '@/lib/position-constants';

/** One plotted dot: a drafted pick with a finite draft position and season points. */
export interface DraftScatterPoint {
  /** `overall_pick_number` — the draft position (x-axis). */
  pick: number;
  /** `total_points` — the player's season points (y-axis). */
  points: number;
  /** `player_name`, or a placeholder when the pick has no name. */
  player: string;
  /** `owner_username` — the manager who drafted the player. */
  manager: string;
  /** `position` — used for the dot color and the position filter. */
  position: string;
}

export interface DraftScatterData {
  points: DraftScatterPoint[];
  /** Distinct positions present among the plotted dots, in fantasy display order. */
  positions: string[];
}

/** Fallback label for a pick whose `player_name` is null/absent. */
export const UNKNOWN_PLAYER = 'Unknown player';

/** Sentinel dropdown value meaning "no position filter". */
export const ALL_POSITIONS = 'ALL';

/** Position abbreviation shown in the tooltip, legend, and filter (DEF renders as D/ST). */
export function positionLabel(position: string): string {
  return position === 'DEF' || position === 'D/ST' ? 'D/ST' : position;
}

/**
 * Order positions QB → RB → WR → TE → D/ST → K → … by `FANTASY_POSITION_ORDER`,
 * with unknown slots last then alphabetical. Sleeper's `DEF` is normalized to the
 * `D/ST` key so both platforms sort a defense into the same spot.
 */
export function comparePositions(a: string, b: string): number {
  const key = (pos: string) => (pos === 'DEF' ? 'D/ST' : pos);
  const oa = FANTASY_POSITION_ORDER[key(a)] ?? Number.POSITIVE_INFINITY;
  const ob = FANTASY_POSITION_ORDER[key(b)] ?? Number.POSITIVE_INFINITY;
  return oa === ob ? a.localeCompare(b) : oa - ob;
}

/**
 * Builds the draft-value scatter from a season's draft picks (FE-038). A pick is
 * plotted only when both axes are finite — `total_points` and `overall_pick_number`
 * must be finite numbers — so picks with no end-of-season scoring row (null
 * `total_points`, e.g. Sleeper D/ST and kickers) are omitted rather than drawn at
 * zero, which would create a false floor of busts. A pure transform of the existing
 * `DRAFT` view.
 */
export function computeDraftScatter(picks: DraftPickItem[]): DraftScatterData {
  const points: DraftScatterPoint[] = [];
  const seen = new Set<string>();

  for (const p of picks) {
    if (
      p.total_points == null ||
      !Number.isFinite(p.total_points) ||
      !Number.isFinite(p.overall_pick_number)
    )
      continue;

    seen.add(p.position);
    points.push({
      pick: p.overall_pick_number,
      points: p.total_points,
      player: p.player_name ?? UNKNOWN_PLAYER,
      manager: p.owner_username,
      position: p.position,
    });
  }

  return { points, positions: [...seen].sort(comparePositions) };
}
