/**
 * Per-team metric assembly (frontend/my-team) — pure, no I/O.
 *
 * Joins the season's precomputed views (standings, matchups, draft, transactions)
 * for one team and produces every number the report card and its insight rules
 * consume. Reuses the shared compute modules from the other features wherever they
 * already exist; the only net-new metric is the power ranking.
 */
import { type GradeResult, computeGrades } from './compute-grade';
import {
  type PowerRankEntry,
  computePowerRankings,
} from './compute-power-rankings';

import type {
  MatchupItem,
  Platform,
  SeasonStandingsItem,
  TransactionItem,
} from '@/components/api/types';
import type { DraftPickItem } from '@/features/draft_grades/api-calls';
import {
  type TeamDraftGrade,
  gradeDraftForTeam,
} from '@/features/draft_grades/compute-draft-grades';
import { computeStartSitReport } from '@/features/lineup_efficiency/compute-lineup-efficiency';
import { computeExpectedWins } from '@/features/schedule_swap/compute-schedule-swap';
import { computeStrengthOfSchedule } from '@/features/season_standings/compute-sos';
import type { WeeklyPlayerPoints } from '@/features/transactions/api-calls';
import { netTradeValueForRoster } from '@/features/transactions/compute-trade-value';
import { isUnplayedMatchup } from '@/lib/matchups';

const RECENT_GAMES = 5;

export interface RecentGame {
  week: number;
  result: 'W' | 'L' | 'T';
  opponent: string;
  teamScore: number;
  oppScore: number;
}

export interface TradeSummary {
  transactionId: string;
  net: number;
  acquired: string[];
  gaveUp: string[];
  week: number;
}

export interface EfficiencyDetail {
  actualSum: number;
  optimalSum: number;
  efficiency: number;
  pointsLeft: number;
  worstWeek: { week: number; pointsLeft: number } | null;
}

export interface TeamMetrics {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  numTeams: number;
  // Record
  wins: number;
  losses: number;
  ties: number;
  record: string;
  winPct: number;
  gamesPlayed: number;
  seed: number;
  // Scoring
  totalPf: number;
  avgPf: number;
  pfRank: number;
  // All-play
  allPlayWins: number;
  allPlayLosses: number;
  allPlayWinPct: number;
  // Luck / schedule
  expectedWins: number | null;
  luck: number | null;
  sos: number | null;
  sosRank: number | null;
  // Lineup efficiency
  efficiency: number | null;
  pointsLeft: number;
  worstBenchWeek: { week: number; pointsLeft: number } | null;
  // Composite views
  powerRank: PowerRankEntry | null;
  grade: GradeResult | null;
  draft: TeamDraftGrade;
  recentForm: RecentGame[];
  trades: {
    best: TradeSummary | null;
    worst: TradeSummary | null;
    tradeCount: number;
    waiverCount: number;
  };
  platform: Platform;
  hasTransactions: boolean;
}

interface TeamSide {
  teamId: string;
  week: number;
  starters: MatchupItem['team_a_starters'];
  bench: MatchupItem['team_a_bench'];
}

/** Both played sides of every matchup (skips unplayed 0–0 placeholders). */
function playedSides(matchups: MatchupItem[]): TeamSide[] {
  const sides: TeamSide[] = [];
  for (const m of matchups) {
    if (isUnplayedMatchup(m)) continue;
    const week = Number(m.week);
    sides.push({
      teamId: m.team_a_id,
      week,
      starters: m.team_a_starters,
      bench: m.team_a_bench,
    });
    sides.push({
      teamId: m.team_b_id,
      week,
      starters: m.team_b_starters,
      bench: m.team_b_bench,
    });
  }
  return sides;
}

/** Season lineup-efficiency detail per team, aggregated over its team-weeks. */
export function computeEfficiencyDetails(
  matchups: MatchupItem[],
): Map<string, EfficiencyDetail> {
  const acc = new Map<string, EfficiencyDetail>();
  for (const side of playedSides(matchups)) {
    const report = computeStartSitReport(side.starters, side.bench);
    if (!report.hasBenchData) continue;
    const d =
      acc.get(side.teamId) ??
      acc
        .set(side.teamId, {
          actualSum: 0,
          optimalSum: 0,
          efficiency: 1,
          pointsLeft: 0,
          worstWeek: null,
        })
        .get(side.teamId)!;
    d.actualSum += report.actualPoints;
    d.optimalSum += report.optimalPoints;
    d.pointsLeft += report.pointsLeft;
    if (!d.worstWeek || report.pointsLeft > d.worstWeek.pointsLeft) {
      d.worstWeek = { week: side.week, pointsLeft: report.pointsLeft };
    }
  }
  for (const d of acc.values()) {
    d.efficiency = d.optimalSum > 0 ? d.actualSum / d.optimalSum : 1;
    d.pointsLeft = Math.round(d.pointsLeft * 100) / 100;
  }
  return acc;
}

/** The selected team's most recent games, newest first. */
function recentFormFor(matchups: MatchupItem[], teamId: string): RecentGame[] {
  const games: RecentGame[] = [];
  for (const m of matchups) {
    if (isUnplayedMatchup(m)) continue;
    const side =
      m.team_a_id === teamId ? 'a' : m.team_b_id === teamId ? 'b' : null;
    if (!side) continue;
    const other = side === 'a' ? 'b' : 'a';
    const teamScore = Number(m[`team_${side}_score`]);
    const oppScore = Number(m[`team_${other}_score`]);
    games.push({
      week: Number(m.week),
      result: teamScore > oppScore ? 'W' : teamScore < oppScore ? 'L' : 'T',
      opponent: m[`team_${other}_display_name`],
      teamScore,
      oppScore,
    });
  }
  return games.sort((a, b) => b.week - a.week).slice(0, RECENT_GAMES);
}

/** Best and worst trade (by net rest-of-season value) for the team, plus counts. */
function tradesFor(
  transactions: TransactionItem[],
  teamId: string,
  weekly: WeeklyPlayerPoints,
): TeamMetrics['trades'] {
  const names = (filterRoster: string, txn: TransactionItem) =>
    txn.adds
      .filter((a) => a.roster_id === filterRoster)
      .map((a) => a.player_name ?? 'Player');

  let best: TradeSummary | null = null;
  let worst: TradeSummary | null = null;
  let tradeCount = 0;
  let waiverCount = 0;

  for (const txn of transactions) {
    const involvesTeam =
      txn.teams.some((t) => t.roster_id === teamId) ||
      txn.adds.some((a) => a.roster_id === teamId) ||
      txn.drops.some((d) => d.roster_id === teamId);
    if (!involvesTeam) continue;

    if (txn.type === 'waiver' || txn.type === 'free_agent') {
      waiverCount += 1;
      continue;
    }
    if (txn.type !== 'trade') continue;

    const net = netTradeValueForRoster(txn, teamId, weekly);
    if (net === null) continue;
    tradeCount += 1;
    const other =
      [...new Set(txn.adds.map((a) => a.roster_id))].find(
        (id) => id !== teamId,
      ) ?? '';
    const summary: TradeSummary = {
      transactionId: txn.transaction_id,
      net,
      acquired: names(teamId, txn),
      gaveUp: other ? names(other, txn) : [],
      week: txn.week,
    };
    if (!best || net > best.net) best = summary;
    if (!worst || net < worst.net) worst = summary;
  }

  // With a single trade, best and worst coincide; keep best, drop worst.
  if (best && best.transactionId === worst?.transactionId) worst = null;

  return { best, worst, tradeCount, waiverCount };
}

export interface TeamMetricsInput {
  teamId: string;
  platform: Platform;
  standings: SeasonStandingsItem[];
  matchups: MatchupItem[];
  draftPicks: DraftPickItem[];
  transactions: TransactionItem[];
  weekly: WeeklyPlayerPoints;
}

/** Assemble every metric for the selected team, or null when it is not in the standings. */
export function computeTeamMetrics(
  input: TeamMetricsInput,
): TeamMetrics | null {
  const { teamId, platform, standings, matchups, draftPicks, transactions } =
    input;
  const me = standings.find((s) => s.team_id === teamId);
  if (!me) return null;

  const numTeams = standings.length;
  const bySeed = [...standings].sort(
    (a, b) =>
      b.wins - a.wins || b.win_pct - a.win_pct || b.total_pf - a.total_pf,
  );
  const seed = bySeed.findIndex((s) => s.team_id === teamId) + 1;
  const byPf = [...standings].sort((a, b) => b.total_pf - a.total_pf);
  const pfRank = byPf.findIndex((s) => s.team_id === teamId) + 1;

  const expectedByTeam = computeExpectedWins(matchups);
  const expectedWins = expectedByTeam[teamId] ?? null;
  const luck = expectedWins !== null ? me.wins - expectedWins : null;

  const sosByTeam = computeStrengthOfSchedule(standings, matchups);
  const sos = sosByTeam[teamId] ?? null;
  const sosValues = Object.entries(sosByTeam).filter(
    (e): e is [string, number] => e[1] !== null,
  );
  const sosRank =
    sos !== null ? sosValues.filter(([, v]) => v > sos).length + 1 : null;

  const efficiencyDetails = computeEfficiencyDetails(matchups);
  const efficiencyByTeam = new Map(
    [...efficiencyDetails].map(([id, d]) => [id, d.efficiency]),
  );
  const myEff = efficiencyDetails.get(teamId) ?? null;

  const powerRank =
    computePowerRankings(matchups).find((e) => e.teamId === teamId) ?? null;
  const grade = computeGrades(standings, efficiencyByTeam).get(teamId) ?? null;
  const draft = gradeDraftForTeam(draftPicks, teamId);
  const recentForm = recentFormFor(matchups, teamId);
  const trades = tradesFor(transactions, teamId, input.weekly);

  return {
    teamId,
    ownerUsername: me.owner_username,
    teamName: me.team_name,
    teamLogo: me.team_logo || null,
    numTeams,
    wins: me.wins,
    losses: me.losses,
    ties: me.ties,
    record: me.record,
    winPct: me.win_pct,
    gamesPlayed: me.games_played,
    seed,
    totalPf: me.total_pf,
    avgPf: me.avg_pf,
    pfRank,
    allPlayWins: me.total_vs_league_wins,
    allPlayLosses: me.total_vs_league_losses,
    allPlayWinPct: me.win_pct_vs_league,
    expectedWins,
    luck,
    sos,
    sosRank,
    efficiency: myEff?.efficiency ?? null,
    pointsLeft: myEff?.pointsLeft ?? 0,
    worstBenchWeek: myEff?.worstWeek ?? null,
    powerRank,
    grade,
    draft,
    recentForm,
    trades,
    platform,
    hasTransactions: platform === 'SLEEPER' && transactions.length > 0,
  };
}
