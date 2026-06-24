import type { MatchupItem, PlayerStat } from '@/components/api/types';
import { POSITION_COLORS } from '@/lib/color-constants';
import { POS_NORMALIZE } from '@/lib/position-constants';

/** One manager's total starter points for a season, split by real position. */
export interface PositionalTeam {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  /** Sum of every starter's points across the season. */
  total: number;
  /** Summed starter points keyed on normalized real position (QB/RB/… or 'Other'). */
  byPosition: Record<string, number>;
}

export interface PositionalScoringData {
  /** Positions actually present, in {@link POSITION_ORDER} (the stacking order). */
  positions: string[];
  /** Managers sorted by total points (highest first), tie-broken on username. */
  teams: PositionalTeam[];
}

/** The catch-all segment for any position without a dedicated color. */
export const OTHER_POSITION = 'Other';

/**
 * Fixed stacking order for the bars: the six standard fantasy positions (the
 * {@link POSITION_COLORS} keys) followed by the {@link OTHER_POSITION} catch-all.
 */
export const POSITION_ORDER = [
  'QB',
  'RB',
  'WR',
  'TE',
  'DEF',
  'K',
  OTHER_POSITION,
] as const;

/** Coerce a starter's points to a finite number, treating junk as 0. */
function points(p: PlayerStat): number {
  const n = Number(p.points_scored);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Bucket a starter into a normalized real position. ESPN's `D/ST` becomes `DEF`
 * via {@link POS_NORMALIZE}; anything without a dedicated {@link POSITION_COLORS}
 * color (e.g. IDP slots) folds into {@link OTHER_POSITION}.
 */
function bucket(p: PlayerStat): string {
  const normalized = POS_NORMALIZE[p.position] ?? p.position;
  return normalized in POSITION_COLORS ? normalized : OTHER_POSITION;
}

interface TeamMeta {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
}

/**
 * Sum each manager's season starter points by real position (FE-036). Every
 * matchup counts — regular-season and playoff weeks alike — so all managers span
 * the same number of weeks; only byes (a side with no finite score) and
 * self-matchup placeholders (`team_a_id === team_b_id`) are skipped. FLEX and
 * superflex points roll into the player's actual position (RB/WR/TE/QB), and any
 * position without a dedicated color folds into {@link OTHER_POSITION}. Managers
 * are returned sorted by total points (highest first), tie-broken on username.
 */
export function computePositionalScoring(
  matchups: MatchupItem[],
): PositionalScoringData {
  const meta = new Map<string, TeamMeta>();
  const byTeam = new Map<string, Record<string, number>>();

  const add = (id: string, starters: PlayerStat[]) => {
    let bucketTotals = byTeam.get(id);
    if (!bucketTotals) {
      bucketTotals = {};
      byTeam.set(id, bucketTotals);
    }
    for (const starter of starters) {
      const key = bucket(starter);
      bucketTotals[key] = (bucketTotals[key] ?? 0) + points(starter);
    }
  };

  for (const m of matchups) {
    if (m.team_a_id === m.team_b_id) continue;
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);
    for (const side of ['a', 'b'] as const) {
      const sideScore = side === 'a' ? aScore : bScore;
      if (!Number.isFinite(sideScore)) continue; // bye
      const id = m[`team_${side}_id`];
      // Names/logos can change across weeks; keep the latest seen.
      meta.set(id, {
        teamId: id,
        ownerUsername: m[`team_${side}_display_name`],
        teamName: m[`team_${side}_team_name`],
        teamLogo: m[`team_${side}_team_logo`],
      });
      add(id, m[`team_${side}_starters`]);
    }
  }

  const teams: PositionalTeam[] = [];
  const present = new Set<string>();
  for (const [id, byPosition] of byTeam) {
    const total = Object.values(byPosition).reduce((sum, v) => sum + v, 0);
    for (const pos of Object.keys(byPosition)) present.add(pos);
    teams.push({ ...meta.get(id)!, total, byPosition });
  }

  teams.sort(
    (a, b) =>
      b.total - a.total || a.ownerUsername.localeCompare(b.ownerUsername),
  );

  const positions = POSITION_ORDER.filter((p) => present.has(p));

  return { positions, teams };
}
