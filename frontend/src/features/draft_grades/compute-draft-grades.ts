/**
 * Draft-grading computation (frontend/draft-grades) — pure, no I/O.
 *
 * Extracted from `draft-grades.tsx` so both the Draft Grades page and the My Team
 * report card grade a team's draft from one shared implementation. A pick is graded
 * on its `draft_rank_delta` (drafted_position_rank − actual_position_rank; positive
 * means the player outperformed where they were drafted).
 */
import type { DraftPickItem } from './api-calls';

// ── Grading thresholds ─────────────────────────────────────────────────────────

export const STEAL_DELTA_MIN = 5; // draft_rank_delta >= this → steal
export const BUST_DELTA_MAX = -5; // draft_rank_delta <= this → potential bust
export const BUST_ROUND_BUFFER = 4; // bust only when picked more than this many rounds before the last
export const BUST_ROUND_MAX = 10; // only flag busts / show alternatives for rounds 1–10
export const AUCTION_BUST_MIN_BID = 5; // auction: only flag busts on players that cost more than this

// ── Predicates ──────────────────────────────────────────────────────────────────

/**
 * A pick is "scorable" for best/worst grading when it has a `draft_rank_delta`.
 * Kickers and defenses are excluded — they carry null analytics (no scoring row).
 */
export function isScorablePick(p: DraftPickItem): boolean {
  return (
    p.position !== 'K' && p.position !== 'D/ST' && p.draft_rank_delta != null
  );
}

/** A steal: an outperforming pick whose delta clears {@link STEAL_DELTA_MIN}. */
export function isStealPick(p: DraftPickItem): boolean {
  return p.draft_rank_delta != null && p.draft_rank_delta >= STEAL_DELTA_MIN;
}

/**
 * Build a bust predicate over a full draft. A bust is an underperforming pick
 * (`draft_rank_delta <= BUST_DELTA_MAX`) that was expensive enough to matter:
 * for auctions, a bid over {@link AUCTION_BUST_MIN_BID}; for snake drafts, a pick
 * made well before the draft's end (within {@link BUST_ROUND_MAX} and more than
 * {@link BUST_ROUND_BUFFER} rounds before the last round). The `isAuction` and
 * `maxRound` context both come from the full pick list.
 */
export function makeIsBustPick(
  allPicks: DraftPickItem[],
): (p: DraftPickItem) => boolean {
  const isAuction = allPicks[0]?.is_auction ?? false;
  const maxRound = allPicks.length
    ? Math.max(...allPicks.map((p) => p.round))
    : 0;
  return (p: DraftPickItem) =>
    p.draft_rank_delta != null &&
    p.draft_rank_delta <= BUST_DELTA_MAX &&
    (isAuction
      ? p.bid_amount > AUCTION_BUST_MIN_BID
      : p.round <= maxRound - BUST_ROUND_BUFFER && p.round <= BUST_ROUND_MAX);
}

// ── Team grade ──────────────────────────────────────────────────────────────────

export interface TeamDraftGrade {
  /** Highest-delta scorable pick for the team, or null when none are scorable. */
  bestPick: DraftPickItem | null;
  /** Lowest-delta scorable pick for the team, or null when none are scorable. */
  worstPick: DraftPickItem | null;
  /** Count of the team's steals. */
  steals: number;
  /** Count of the team's busts (using the whole-draft bust predicate). */
  busts: number;
  /** The team's scorable picks (used to grade best/worst). */
  scorablePicks: DraftPickItem[];
}

/**
 * Grade one team's draft. `teamId` is the roster/`team_id`. Best/worst are the
 * extreme `draft_rank_delta` scorable picks; steals/busts are counts over all of
 * the team's picks, using the same thresholds as the Draft Grades page.
 */
export function gradeDraftForTeam(
  allPicks: DraftPickItem[],
  teamId: string,
): TeamDraftGrade {
  const picks = allPicks.filter((p) => p.team_id === teamId);
  const scorablePicks = picks.filter(isScorablePick);

  const bestPick = scorablePicks.length
    ? scorablePicks.reduce((best, p) =>
        (p.draft_rank_delta ?? 0) > (best.draft_rank_delta ?? 0) ? p : best,
      )
    : null;
  const worstPick = scorablePicks.length
    ? scorablePicks.reduce((worst, p) =>
        (p.draft_rank_delta ?? 0) < (worst.draft_rank_delta ?? 0) ? p : worst,
      )
    : null;

  const isBust = makeIsBustPick(allPicks);
  const busts = picks.filter(isBust).length;
  const steals = picks.filter(isStealPick).length;

  return { bestPick, worstPick, steals, busts, scorablePicks };
}
