/**
 * Power rankings (frontend/my-team) — pure, no I/O.
 *
 * The one net-new metric the My Team page introduces. A team's power score is a
 * normalized blend of its average points-for (0.5), all-play win % (0.3), and
 * last-3-week form (0.2), computed entirely from a season's regular-season
 * `MATCHUPS`. Teams are ranked by score; week-over-week movement is the change in
 * rank versus the same ranking computed through the previous week.
 */
import type { MatchupItem } from '@/components/api/types';
import { isRegularSeason } from '@/features/schedule_swap/compute-schedule-swap';
import { isUnplayedMatchup } from '@/lib/matchups';

const W_PF = 0.5;
const W_ALLPLAY = 0.3;
const W_FORM = 0.2;
const FORM_WEEKS = 3;

export interface PowerRankEntry {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  /** Blended power score, 0–100 for display. */
  score: number;
  /** 1-based rank (1 = strongest). */
  rank: number;
  /** Rank through the previous week, or null when there is no prior week. */
  previousRank: number | null;
  /** previousRank − rank: positive = moved up, negative = down, 0 = flat/unknown. */
  movement: number;
  avgPf: number;
  allPlayWinPct: number;
  formWinPct: number;
}

interface TeamWeek {
  teamId: string;
  week: number;
  score: number;
  result: 'W' | 'L' | 'T';
}

interface TeamInfo {
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
}

interface TeamMetrics {
  avgPf: number;
  allPlayWinPct: number;
  formWinPct: number;
  score: number;
}

/** Flatten a season's regular-season matchups into per-team weekly results. */
function collectTeamWeeks(matchups: MatchupItem[]): {
  teamWeeks: TeamWeek[];
  info: Map<string, TeamInfo>;
} {
  const teamWeeks: TeamWeek[] = [];
  const info = new Map<string, TeamInfo>();
  for (const m of matchups) {
    if (!isRegularSeason(m) || isUnplayedMatchup(m)) continue;
    const week = Number(m.week);
    const a = Number(m.team_a_score);
    const b = Number(m.team_b_score);
    teamWeeks.push({
      teamId: m.team_a_id,
      week,
      score: a,
      result: a > b ? 'W' : a < b ? 'L' : 'T',
    });
    teamWeeks.push({
      teamId: m.team_b_id,
      week,
      score: b,
      result: b > a ? 'W' : b < a ? 'L' : 'T',
    });
    info.set(m.team_a_id, {
      ownerUsername: m.team_a_display_name,
      teamName: m.team_a_team_name,
      teamLogo: m.team_a_team_logo,
    });
    info.set(m.team_b_id, {
      ownerUsername: m.team_b_display_name,
      teamName: m.team_b_team_name,
      teamLogo: m.team_b_team_logo,
    });
  }
  return { teamWeeks, info };
}

/** Min–max normalize to 0–1; when every value is equal, return a neutral 0.5. */
function normalize(values: Map<string, number>): Map<string, number> {
  const nums = [...values.values()];
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min;
  const out = new Map<string, number>();
  for (const [id, v] of values) {
    out.set(id, span === 0 ? 0.5 : (v - min) / span);
  }
  return out;
}

/** Compute each team's blended power score from a set of team-weeks. */
function scoreTeams(teamWeeks: TeamWeek[]): Map<string, TeamMetrics> {
  const byWeek = new Map<number, TeamWeek[]>();
  const byTeam = new Map<string, TeamWeek[]>();
  for (const tw of teamWeeks) {
    (byWeek.get(tw.week) ?? byWeek.set(tw.week, []).get(tw.week)!).push(tw);
    (byTeam.get(tw.teamId) ?? byTeam.set(tw.teamId, []).get(tw.teamId)!).push(
      tw,
    );
  }

  // All-play: every week, each team is scored against every other team that week.
  const allPlayWins = new Map<string, number>();
  const allPlayGames = new Map<string, number>();
  for (const week of byWeek.values()) {
    for (const t of week) {
      let wins = 0;
      for (const o of week) {
        if (o.teamId === t.teamId) continue;
        if (t.score > o.score) wins += 1;
        else if (t.score === o.score) wins += 0.5;
      }
      allPlayWins.set(t.teamId, (allPlayWins.get(t.teamId) ?? 0) + wins);
      allPlayGames.set(
        t.teamId,
        (allPlayGames.get(t.teamId) ?? 0) + (week.length - 1),
      );
    }
  }

  const avgPf = new Map<string, number>();
  const allPlay = new Map<string, number>();
  const form = new Map<string, number>();
  for (const [teamId, games] of byTeam) {
    avgPf.set(teamId, games.reduce((s, g) => s + g.score, 0) / games.length);
    const ap = allPlayGames.get(teamId) ?? 0;
    allPlay.set(teamId, ap > 0 ? (allPlayWins.get(teamId) ?? 0) / ap : 0);
    const last = [...games].sort((a, b) => a.week - b.week).slice(-FORM_WEEKS);
    const pts = last.reduce(
      (s, g) => s + (g.result === 'W' ? 1 : g.result === 'T' ? 0.5 : 0),
      0,
    );
    form.set(teamId, last.length > 0 ? pts / last.length : 0);
  }

  const pfNorm = normalize(avgPf);
  const out = new Map<string, TeamMetrics>();
  for (const teamId of byTeam.keys()) {
    const score =
      W_PF * (pfNorm.get(teamId) ?? 0) +
      W_ALLPLAY * (allPlay.get(teamId) ?? 0) +
      W_FORM * (form.get(teamId) ?? 0);
    out.set(teamId, {
      avgPf: avgPf.get(teamId) ?? 0,
      allPlayWinPct: allPlay.get(teamId) ?? 0,
      formWinPct: form.get(teamId) ?? 0,
      score,
    });
  }
  return out;
}

/** teamId → 1-based rank, ordered by score desc then teamId for determinism. */
function rankMap(metrics: Map<string, TeamMetrics>): Map<string, number> {
  const order = [...metrics.entries()].sort(
    (a, b) => b[1].score - a[1].score || a[0].localeCompare(b[0]),
  );
  return new Map(order.map(([id], i) => [id, i + 1]));
}

/** Full power ranking for a season, strongest first, with week-over-week movement. */
export function computePowerRankings(
  matchups: MatchupItem[],
): PowerRankEntry[] {
  const { teamWeeks, info } = collectTeamWeeks(matchups);
  if (teamWeeks.length === 0) return [];

  const maxWeek = Math.max(...teamWeeks.map((t) => t.week));
  const current = scoreTeams(teamWeeks);
  const priorWeeks = teamWeeks.filter((t) => t.week < maxWeek);
  const priorRanks = priorWeeks.length ? rankMap(scoreTeams(priorWeeks)) : null;

  const order = [...current.entries()].sort(
    (a, b) => b[1].score - a[1].score || a[0].localeCompare(b[0]),
  );

  return order.map(([teamId, m], i) => {
    const rank = i + 1;
    const previousRank = priorRanks?.get(teamId) ?? null;
    return {
      teamId,
      ownerUsername: info.get(teamId)?.ownerUsername ?? teamId,
      teamName: info.get(teamId)?.teamName ?? '',
      teamLogo: info.get(teamId)?.teamLogo ?? null,
      score: Math.round(m.score * 1000) / 10,
      rank,
      previousRank,
      movement: previousRank !== null ? previousRank - rank : 0,
      avgPf: m.avgPf,
      allPlayWinPct: m.allPlayWinPct,
      formWinPct: m.formWinPct,
    };
  });
}

/** The power-ranking entry for one team, or null when it has no ranked games. */
export function powerRankForTeam(
  matchups: MatchupItem[],
  teamId: string,
): PowerRankEntry | null {
  return (
    computePowerRankings(matchups).find((e) => e.teamId === teamId) ?? null
  );
}
