import type { MatchupItem } from '@/components/api/types';
import { isUnplayedMatchup } from '@/lib/matchups';

/** A win/loss/tie tally over some set of (possibly swapped) games. */
export interface SwapRecord {
  wins: number;
  losses: number;
  ties: number;
  games: number;
}

/** A team in the matrix, with its actual (diagonal) regular-season record. */
export interface SwapTeam {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  actual: SwapRecord;
}

export interface ScheduleSwapData {
  /** Teams ordered by actual wins desc, then win%, then username. */
  teams: SwapTeam[];
  /**
   * `matrix.get(rowTeamId).get(colTeamId)` = the row team's record using the
   * column manager's schedule. The diagonal (`row === col`) is the actual record.
   */
  matrix: Map<string, Map<string, SwapRecord>>;
}

/** A regular-season game is one with no playoff tier (`NONE` or absent). */
function isRegularSeason(m: MatchupItem): boolean {
  return !m.playoff_tier_type || m.playoff_tier_type === 'NONE';
}

function winPct(r: SwapRecord): number {
  return r.games > 0 ? (r.wins + 0.5 * r.ties) / r.games : 0;
}

/**
 * Build the schedule-swap matrix from a season's matchups (frontend/schedule-swap-simulator).
 *
 * Holds every team's own weekly scores fixed and replays them against every
 * other manager's schedule. For the row team `R` under column manager `C`, each
 * week `C` played, `R` faces whoever `C` faced — except when that opponent is `R`
 * itself, in which case `R` takes `C`'s place and faces `C`. Only regular-season
 * games count; weeks where either side has no score (a bye) are skipped.
 */
export function computeScheduleSwap(matchups: MatchupItem[]): ScheduleSwapData {
  const teamInfo = new Map<string, Omit<SwapTeam, 'actual'>>();
  // week -> teamId -> score, and week -> teamId -> opponentTeamId
  const scoreByWeek = new Map<string, Map<string, number>>();
  const oppByWeek = new Map<string, Map<string, string>>();

  for (const m of matchups) {
    if (!isRegularSeason(m)) continue;
    // Unplayed 0-0 placeholder weeks add no real scores to swap against.
    if (isUnplayedMatchup(m)) continue;
    const week = m.week;
    if (!scoreByWeek.has(week)) scoreByWeek.set(week, new Map());
    if (!oppByWeek.has(week)) oppByWeek.set(week, new Map());
    const scores = scoreByWeek.get(week)!;
    const opps = oppByWeek.get(week)!;

    for (const side of ['a', 'b'] as const) {
      const other = side === 'a' ? 'b' : 'a';
      const id = m[`team_${side}_id`];
      scores.set(id, Number(m[`team_${side}_score`]));
      opps.set(id, m[`team_${other}_id`]);
      // Names can change across weeks; keep the latest seen.
      teamInfo.set(id, {
        teamId: id,
        ownerUsername: m[`team_${side}_display_name`],
        teamName: m[`team_${side}_team_name`],
        teamLogo: m[`team_${side}_team_logo`],
      });
    }
  }

  const teamIds = [...teamInfo.keys()];
  const matrix = new Map<string, Map<string, SwapRecord>>();

  for (const rowId of teamIds) {
    const row = new Map<string, SwapRecord>();
    for (const colId of teamIds) {
      const rec: SwapRecord = { wins: 0, losses: 0, ties: 0, games: 0 };
      for (const [week, opps] of oppByWeek) {
        const colOpp = opps.get(colId); // the column manager's opponent that week
        if (colOpp === undefined) continue; // column manager had a bye
        // Borrowing a schedule that pits the row team against itself: it takes
        // the schedule owner's slot and faces the schedule owner instead.
        const oppId = colOpp === rowId ? colId : colOpp;
        const scores = scoreByWeek.get(week)!;
        const myScore = scores.get(rowId);
        const oppScore = scores.get(oppId);
        if (myScore === undefined || oppScore === undefined) continue; // bye
        rec.games++;
        if (myScore > oppScore) rec.wins++;
        else if (myScore < oppScore) rec.losses++;
        else rec.ties++;
      }
      row.set(colId, rec);
    }
    matrix.set(rowId, row);
  }

  const teams: SwapTeam[] = teamIds.map((id) => ({
    ...teamInfo.get(id)!,
    actual: matrix.get(id)!.get(id)!,
  }));
  teams.sort(
    (a, b) =>
      b.actual.wins - a.actual.wins ||
      winPct(b.actual) - winPct(a.actual) ||
      a.ownerUsername.localeCompare(b.ownerUsername),
  );

  return { teams, matrix };
}

/**
 * Each team's expected wins (frontend/season-standings): the average number of wins it would
 * record across every manager's schedule in the season — a schedule-independent
 * estimate of how many games it "should" have won given its own weekly scores.
 * Derived from the schedule-swap matrix ([frontend/schedule-swap-simulator]) by averaging each row team's
 * win totals over all columns (its own schedule included).
 *
 * Returns a `team_id -> expected wins` map covering every team with
 * regular-season matchups; teams absent from that map (e.g. no matchups) have no
 * simulated games.
 */
export function computeExpectedWins(
  matchups: MatchupItem[],
): Record<string, number> {
  const { teams, matrix } = computeScheduleSwap(matchups);
  const expectedWinsById: Record<string, number> = {};
  for (const team of teams) {
    const winTotals = [...matrix.get(team.teamId)!.values()].map((r) => r.wins);
    expectedWinsById[team.teamId] =
      winTotals.reduce((a, b) => a + b, 0) / winTotals.length;
  }
  return expectedWinsById;
}

/** Format a record as `W-L` or `W-L-T` when there are ties. */
export function formatRecord(r: SwapRecord): string {
  return r.ties > 0
    ? `${r.wins}-${r.losses}-${r.ties}`
    : `${r.wins}-${r.losses}`;
}
