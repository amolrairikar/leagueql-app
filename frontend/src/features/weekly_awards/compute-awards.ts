import type { MatchupItem } from '@/components/api/types';
import { isUnplayedMatchup } from '@/lib/matchups';

/** The per-week award types, in display order (frontend/weekly-awards). */
export type AwardKey =
  'highest' | 'lowest' | 'blowout' | 'narrowest' | 'bestLoss' | 'worstWin';

export interface AwardDef {
  key: AwardKey;
  label: string;
  /** Short description used for column tooltips. */
  short: string;
}

/** Award metadata in the order cards and tally columns render. */
export const AWARD_DEFS: AwardDef[] = [
  {
    key: 'highest',
    label: 'Highest Score',
    short: 'Highest single-team score',
  },
  { key: 'lowest', label: 'Lowest Score', short: 'Lowest single-team score' },
  { key: 'blowout', label: 'Biggest Blowout', short: 'Largest winning margin' },
  {
    key: 'narrowest',
    label: 'Narrowest Win',
    short: 'Smallest winning margin',
  },
  { key: 'bestLoss', label: 'Best Loss', short: 'Highest-scoring losing team' },
  { key: 'worstWin', label: 'Worst Win', short: 'Lowest-scoring winning team' },
];

/** A single award's recipient for one week. */
export interface AwardWinner {
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  teamId: string;
  statText: string;
}

/** A manager's running award counts through the active week. */
export interface TallyRow {
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  teamId: string;
  counts: Record<AwardKey, number>;
}

/** The manager on the longest active win streak as of the active week. */
export interface StreakHolder {
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  teamId: string;
  length: number;
}

export interface WeeklyAwardsData {
  /** All weeks present in the data, ascending. */
  weeks: number[];
  /** The week the award cards are shown for (resolved from the selection). */
  activeWeek: number;
  /** One winner per award type for the active week (absent when not computable). */
  awards: Partial<Record<AwardKey, AwardWinner>>;
  /**
   * Award counts per team across weeks 1…activeWeek, sorted by manager name.
   * Counts are not summed: the awards mix desirable and undesirable outcomes, so
   * a combined total would be misleading.
   */
  tally: TallyRow[];
  /** Manager on the longest active win streak (≥ 2) through the active week, else null. */
  longestStreak: StreakHolder | null;
}

/** A team's score on one side of a matchup. */
interface SideScore {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  score: number;
}

/** A decided (non-tied) matchup, split into its winner and loser side. */
interface Decided {
  winner: SideScore;
  loser: SideScore;
  margin: number;
}

type TeamMeta = Omit<SideScore, 'score'>;

const AWARD_KEYS = AWARD_DEFS.map((d) => d.key);

function emptyCounts(): Record<AwardKey, number> {
  return {
    highest: 0,
    lowest: 0,
    blowout: 0,
    narrowest: 0,
    bestLoss: 0,
    worstWin: 0,
  };
}

/**
 * The two scored sides of a real matchup, or `null` for a bye/placeholder.
 *
 * Skips self-matchup placeholders (`team_a_id === team_b_id`), unplayed `0-0`
 * placeholder weeks, and rows where either side has no finite score, so neither
 * byes nor future/unplayed weeks feed an award, tally, or streak.
 */
function sides(m: MatchupItem): [SideScore, SideScore] | null {
  if (m.team_a_id === m.team_b_id) return null;
  if (isUnplayedMatchup(m)) return null;
  const a = Number(m.team_a_score);
  const b = Number(m.team_b_score);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  return [
    {
      teamId: m.team_a_id,
      ownerUsername: m.team_a_display_name,
      teamName: m.team_a_team_name,
      teamLogo: m.team_a_team_logo,
      score: a,
    },
    {
      teamId: m.team_b_id,
      ownerUsername: m.team_b_display_name,
      teamName: m.team_b_team_name,
      teamLogo: m.team_b_team_logo,
      score: b,
    },
  ];
}

/**
 * Pick the "better" of two sides by score (`dir` = 1 prefers higher, -1 lower),
 * breaking ties deterministically on `ownerUsername` — mirroring the sort
 * tiebreak in `compute-schedule-swap.ts`.
 */
function pickSide(a: SideScore, b: SideScore, dir: 1 | -1): SideScore {
  if (a.score !== b.score) return dir * (a.score - b.score) > 0 ? a : b;
  return a.ownerUsername.localeCompare(b.ownerUsername) <= 0 ? a : b;
}

/**
 * Pick the decided matchup with the extreme margin (`dir` = 1 largest, -1
 * smallest), breaking ties on the winner's score then the winner's username.
 */
function pickDecided(list: Decided[], dir: 1 | -1): Decided | null {
  return list.reduce<Decided | null>((best, d) => {
    if (best === null) return d;
    if (d.margin !== best.margin) {
      return dir * (d.margin - best.margin) > 0 ? d : best;
    }
    if (d.winner.score !== best.winner.score) {
      return d.winner.score > best.winner.score ? d : best;
    }
    return d.winner.ownerUsername.localeCompare(best.winner.ownerUsername) < 0
      ? d
      : best;
  }, null);
}

function toWinner(s: SideScore, statText: string): AwardWinner {
  return {
    ownerUsername: s.ownerUsername,
    teamName: s.teamName,
    teamLogo: s.teamLogo,
    teamId: s.teamId,
    statText,
  };
}

/** Compute every award type for a single week's matchups. */
function computeWeekAwards(
  weekMatchups: MatchupItem[],
): Partial<Record<AwardKey, AwardWinner>> {
  const allSides: SideScore[] = [];
  const decided: Decided[] = [];
  for (const m of weekMatchups) {
    const pair = sides(m);
    if (!pair) continue;
    const [a, b] = pair;
    allSides.push(a, b);
    if (a.score !== b.score) {
      const [winner, loser] = a.score > b.score ? [a, b] : [b, a];
      decided.push({ winner, loser, margin: Math.abs(a.score - b.score) });
    }
  }

  const awards: Partial<Record<AwardKey, AwardWinner>> = {};
  if (allSides.length === 0) return awards;

  const highest = allSides.reduce((x, y) => pickSide(x, y, 1));
  awards.highest = toWinner(highest, `${highest.score.toFixed(2)} pts`);
  const lowest = allSides.reduce((x, y) => pickSide(x, y, -1));
  awards.lowest = toWinner(lowest, `${lowest.score.toFixed(2)} pts`);

  const blowout = pickDecided(decided, 1);
  if (blowout) {
    awards.blowout = toWinner(
      blowout.winner,
      `Won by ${blowout.margin.toFixed(2)} pts`,
    );
  }
  const narrow = pickDecided(decided, -1);
  if (narrow) {
    awards.narrowest = toWinner(
      narrow.winner,
      `Won by ${narrow.margin.toFixed(2)} pts`,
    );
  }

  if (decided.length > 0) {
    const bestLoss = decided
      .map((d) => d.loser)
      .reduce((x, y) => pickSide(x, y, 1));
    awards.bestLoss = toWinner(
      bestLoss,
      `Lost with ${bestLoss.score.toFixed(2)} pts`,
    );
    const worstWin = decided
      .map((d) => d.winner)
      .reduce((x, y) => pickSide(x, y, -1));
    awards.worstWin = toWinner(
      worstWin,
      `Won with ${worstWin.score.toFixed(2)} pts`,
    );
  }

  return awards;
}

/**
 * Build the weekly awards + running tally from a season's matchups (frontend/weekly-awards).
 *
 * Awards are computed per week for every navigable week (regular season and
 * playoffs). The active week's award cards come from `selectedWeek` (defaulting
 * to the latest week). The tally sums award counts across weeks `1 … activeWeek`,
 * and the longest active streak is the trailing run of wins each team carries
 * into `activeWeek`. Byes and tied matchups are excluded per the award rules.
 */
export function computeWeeklyAwards(
  matchups: MatchupItem[],
  selectedWeek: number | null,
): WeeklyAwardsData {
  const byWeek = new Map<number, MatchupItem[]>();
  for (const m of matchups) {
    const wk = parseInt(m.week, 10);
    if (Number.isNaN(wk)) continue;
    if (!byWeek.has(wk)) byWeek.set(wk, []);
    byWeek.get(wk)!.push(m);
  }

  const weeks = [...byWeek.keys()].sort((a, b) => a - b);
  const latestWeek = weeks[weeks.length - 1] ?? 1;
  const activeWeek = selectedWeek ?? latestWeek;

  const counts = new Map<string, Record<AwardKey, number>>();
  const teamMeta = new Map<string, TeamMeta>();
  // Ordered W/L/T results per team across weeks 1…activeWeek (for streaks).
  const results = new Map<string, ('W' | 'L' | 'T')[]>();

  for (const wk of weeks) {
    if (wk > activeWeek) continue;
    const weekMatchups = byWeek.get(wk)!;

    for (const m of weekMatchups) {
      const pair = sides(m);
      if (!pair) continue;
      const [a, b] = pair;
      // Names can change across weeks; keep the latest seen.
      teamMeta.set(a.teamId, {
        teamId: a.teamId,
        ownerUsername: a.ownerUsername,
        teamName: a.teamName,
        teamLogo: a.teamLogo,
      });
      teamMeta.set(b.teamId, {
        teamId: b.teamId,
        ownerUsername: b.ownerUsername,
        teamName: b.teamName,
        teamLogo: b.teamLogo,
      });
      const aRes = a.score > b.score ? 'W' : a.score < b.score ? 'L' : 'T';
      const bRes = aRes === 'W' ? 'L' : aRes === 'L' ? 'W' : 'T';
      if (!results.has(a.teamId)) results.set(a.teamId, []);
      if (!results.has(b.teamId)) results.set(b.teamId, []);
      results.get(a.teamId)!.push(aRes);
      results.get(b.teamId)!.push(bRes);
    }

    const weekAwards = computeWeekAwards(weekMatchups);
    for (const key of AWARD_KEYS) {
      const winner = weekAwards[key];
      if (!winner) continue;
      if (!counts.has(winner.teamId)) counts.set(winner.teamId, emptyCounts());
      counts.get(winner.teamId)![key] += 1;
    }
  }

  const tally: TallyRow[] = [...teamMeta.values()].map((meta) => ({
    ...meta,
    counts: counts.get(meta.teamId) ?? emptyCounts(),
  }));
  tally.sort((x, y) => x.ownerUsername.localeCompare(y.ownerUsername));

  let longestStreak: StreakHolder | null = null;
  for (const [teamId, res] of results) {
    let run = 0;
    for (let i = res.length - 1; i >= 0; i--) {
      if (res[i] === 'W') run++;
      else break;
    }
    if (run < 2) continue;
    const meta = teamMeta.get(teamId)!;
    if (
      longestStreak === null ||
      run > longestStreak.length ||
      (run === longestStreak.length &&
        meta.ownerUsername.localeCompare(longestStreak.ownerUsername) < 0)
    ) {
      longestStreak = { ...meta, length: run };
    }
  }

  const awards = computeWeekAwards(byWeek.get(activeWeek) ?? []);

  return { weeks, activeWeek, awards, tally, longestStreak };
}
