import type { MatchupItem, PlayerStat } from '@/components/api/types';
import {
  buildTeamScoring,
  winProbability,
  type TeamScoring,
} from '@/features/playoff_race_predictor/compute-projection';
import { isRegularSeason } from '@/features/schedule_swap/compute-schedule-swap';
import { isUnplayedMatchup } from '@/lib/matchups';

/** How many of a team's most recent games the preview's "recent form" shows. */
const RECENT_FORM_GAMES = 5;
/** How many top scorers per team the preview lists. */
const TOP_SCORERS = 3;

/** One played game from a single team's perspective. */
export interface FormGame {
  week: number;
  result: 'W' | 'L' | 'T';
  points: number;
  oppPoints: number;
}

/** A team's points scored in a single week. */
export interface WeekPoints {
  week: number;
  points: number;
}

/** A player's season scoring for one team, aggregated across played games. */
export interface TopScorer {
  playerId: number;
  name: string;
  position: string;
  total: number;
  games: number;
}

/** Everything the preview shows about one team, derived from played games. */
export interface TeamPreviewStats {
  teamId: string;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  /** Win fraction 0..1 (ties count as half); 0 when no games played. */
  winPct: number;
  /** Average points for; 0 when no games played. */
  avgPf: number;
  /** Average points against; 0 when no games played. */
  avgPa: number;
  /** Highest single-game score; 0 when no games played. */
  highScore: number;
  /** Season scoring distribution (mean/std), absent with no scoring history. */
  scoring?: TeamScoring;
  /** Points scored per played week, ascending by week. */
  weekly: WeekPoints[];
  /** Up to {@link RECENT_FORM_GAMES} most recent played games, ascending by week. */
  recentForm: FormGame[];
  /** Up to {@link TOP_SCORERS} highest-scoring players this season, total desc. */
  topScorers: TopScorer[];
}

/** League-average points scored in a single week. */
export interface LeagueWeekAvg {
  week: number;
  avg: number;
}

/** The full head-to-head preview for two teams in a season. */
export interface MatchupPreviewData {
  teamA: TeamPreviewStats;
  teamB: TeamPreviewStats;
  /** Win probability 0..1 for team A / team B (sum to 1; 0.5 each with no data). */
  winProbA: number;
  winProbB: number;
  /** Projected score (scoring mean) for each team, null with no scoring history. */
  projA: number | null;
  projB: number | null;
  /** League-average points per week, ascending by week. */
  leagueWeekly: LeagueWeekAvg[];
}

/** A team's played, regular-season games with that team on either side. */
type Side = 'a' | 'b';

function playedRegularSeason(matchups: MatchupItem[]): MatchupItem[] {
  return matchups.filter((m) => isRegularSeason(m) && !isUnplayedMatchup(m));
}

function sideOf(m: MatchupItem, teamId: string): Side | null {
  if (m.team_a_id === teamId) return 'a';
  if (m.team_b_id === teamId) return 'b';
  return null;
}

function buildTeamStats(
  teamId: string,
  playedReg: MatchupItem[],
  scoring: Map<string, TeamScoring> | undefined,
): TeamPreviewStats {
  let wins = 0;
  let losses = 0;
  let ties = 0;
  let pfSum = 0;
  let paSum = 0;
  let highScore = 0;
  const weekly: WeekPoints[] = [];
  const allForm: FormGame[] = [];
  const players = new Map<number, TopScorer>();

  const games = playedReg
    .map((m) => ({ m, side: sideOf(m, teamId) }))
    .filter((g): g is { m: MatchupItem; side: Side } => g.side !== null)
    .sort((x, y) => Number(x.m.week) - Number(y.m.week));

  for (const { m, side } of games) {
    const other: Side = side === 'a' ? 'b' : 'a';
    const points = Number(m[`team_${side}_score`]);
    const oppPoints = Number(m[`team_${other}_score`]);
    const week = Number(m.week);

    pfSum += points;
    paSum += oppPoints;
    if (points > highScore) highScore = points;

    const result: FormGame['result'] =
      points > oppPoints ? 'W' : points < oppPoints ? 'L' : 'T';
    if (result === 'W') wins++;
    else if (result === 'L') losses++;
    else ties++;

    weekly.push({ week, points });
    allForm.push({ week, result, points, oppPoints });

    const starters: PlayerStat[] = m[`team_${side}_starters`] ?? [];
    for (const p of starters) {
      const cur = players.get(p.player_id);
      if (cur) {
        cur.total += Number(p.points_scored);
        cur.games += 1;
        cur.name = p.full_name;
        cur.position = p.position;
      } else {
        players.set(p.player_id, {
          playerId: p.player_id,
          name: p.full_name,
          position: p.position,
          total: Number(p.points_scored),
          games: 1,
        });
      }
    }
  }

  const gp = wins + losses + ties;
  const topScorers = [...players.values()]
    .sort((a, b) => b.total - a.total)
    .slice(0, TOP_SCORERS);

  return {
    teamId,
    wins,
    losses,
    ties,
    record: `${wins}-${losses}-${ties}`,
    winPct: gp > 0 ? (wins + 0.5 * ties) / gp : 0,
    avgPf: gp > 0 ? pfSum / gp : 0,
    avgPa: gp > 0 ? paSum / gp : 0,
    highScore,
    scoring: scoring?.get(teamId),
    weekly,
    recentForm: allForm.slice(-RECENT_FORM_GAMES),
    topScorers,
  };
}

function leagueWeeklyAverages(playedReg: MatchupItem[]): LeagueWeekAvg[] {
  const sums = new Map<number, { sum: number; count: number }>();
  const add = (week: number, score: number): void => {
    const cur = sums.get(week);
    if (cur) {
      cur.sum += score;
      cur.count += 1;
    } else {
      sums.set(week, { sum: score, count: 1 });
    }
  };
  for (const m of playedReg) {
    const week = Number(m.week);
    add(week, Number(m.team_a_score));
    add(week, Number(m.team_b_score));
  }
  return [...sums.entries()]
    .map(([week, { sum, count }]) => ({
      week,
      avg: count > 0 ? sum / count : 0,
    }))
    .sort((a, b) => a.week - b.week);
}

/**
 * Builds the head-to-head preview for two teams in one season, entirely from the
 * season's matchups. Records, points-for/against, recent form, weekly scoring, and
 * top scorers are derived from each team's played, regular-season games; the scoring
 * distribution and win probability reuse the playoff predictor's model
 * ({@link buildTeamScoring}, {@link winProbability}), which falls back to a coin flip
 * when there is no scoring history yet (e.g. the season's first week).
 */
export function buildMatchupPreview(
  matchups: MatchupItem[],
  teamAId: string,
  teamBId: string,
): MatchupPreviewData {
  const playedReg = playedRegularSeason(matchups);
  const scoring = buildTeamScoring(playedReg);

  const teamA = buildTeamStats(teamAId, playedReg, scoring);
  const teamB = buildTeamStats(teamBId, playedReg, scoring);

  const winProbA = winProbability(scoring, teamAId, teamBId);

  return {
    teamA,
    teamB,
    winProbA,
    winProbB: 1 - winProbA,
    projA: teamA.scoring?.mean ?? null,
    projB: teamB.scoring?.mean ?? null,
    leagueWeekly: leagueWeeklyAverages(playedReg),
  };
}
