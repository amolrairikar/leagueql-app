/**
 * Power-rankings computation (frontend/power-rankings) — pure, no I/O.
 *
 * Ranks every team in a season by a weighted blend of four components, each on a 0–100
 * scale: record, points scored, recent form, and lineup efficiency. The
 * rankings are computed for every "cut" (games through week `k`), so a week's rank can be
 * compared with the previous week's and trended over the last six weeks. Only played
 * regular-season games count.
 */
import type { MatchupItem } from '@/components/api/types';
import { computeStartSitReport } from '@/features/lineup_efficiency/compute-lineup-efficiency';
import { computeScheduleSwap } from '@/features/schedule_swap/compute-schedule-swap';
import { isRegularSeasonMatchup, isUnplayedMatchup } from '@/lib/matchups';

export type ComponentKey = 'record' | 'points' | 'form' | 'efficiency';

export interface ComponentDefinition {
  key: ComponentKey;
  label: string;
  /** Share of the power score, in percent; the weights sum to 100. */
  weight: number;
  description: string;
}

export const POWER_COMPONENTS: ComponentDefinition[] = [
  {
    key: 'record',
    label: 'Record',
    weight: 35,
    description: 'Win percentage so far this season, multiplied by 100.',
  },
  {
    key: 'points',
    label: 'Points scored',
    weight: 30,
    description:
      'Total points for, the steadiest signal of team strength, on a scale from 0-100.',
  },
  {
    key: 'form',
    label: 'Recent form',
    weight: 20,
    description:
      'Average score over the last three weeks, on a scale from 0-100.',
  },
  {
    key: 'efficiency',
    label: 'Lineup efficiency',
    weight: 15,
    description:
      "How close each week's lineup came to the best possible one, on a scale from 0-100.",
  },
];

/** Number of most recent played weeks that make up "recent form". */
const FORM_WEEKS = 3;
/** Number of weeks shown in a rank trend. */
const TREND_WEEKS = 6;
/** Places apart between power rank and record rank before a team is flagged. */
const VERDICT_THRESHOLD = 2;

export type Verdict = 'underrated' | 'overrated' | 'on-the-mark';

export interface ComponentScore {
  key: ComponentKey;
  label: string;
  weight: number;
  /** 0–100 score, or `null` when this component is unavailable for the team. */
  value: number | null;
  /** Change since the previous week's rankings, or `null` when either side is unavailable. */
  delta: number | null;
}

export interface PowerRow {
  teamId: string;
  teamName: string;
  managerName: string;
  teamLogo: string | null;
  wins: number;
  losses: number;
  ties: number;
  /** `W-L` or `W-L-T` when there are ties. */
  record: string;
  score: number;
  rank: number;
  /** Rank in the previous week's rankings, or `null` at the earliest week. */
  prevRank: number | null;
  /** Places gained since the previous week (positive = moved up); 0 when there is no previous rank. */
  movement: number;
  /** Rank by record alone (wins with ties as half, then points for). */
  recordRank: number;
  verdict: Verdict;
  /** Up to the last six weeks of ranks, oldest first, ending at the current rank. */
  trend: number[];
  components: ComponentScore[];
  expectedWins: number;
  /** Expected wins and losses, formatted to one decimal each. */
  expectedRecord: string;
  /** A short written read on the team. */
  blurb: string;
}

export interface PowerRankings {
  /** Played regular-season weeks, ascending. Rankings exist for each of these cuts. */
  playedWeeks: number[];
  /** Rankings from games through `week`, best first; empty when `week` is not a played week. */
  through(week: number): PowerRow[];
}

interface TeamWeek {
  week: number;
  score: number;
  /** Win = 1, tie = 0.5, loss = 0. */
  result: number;
  actualLineup: number;
  optimalLineup: number;
  hasBench: boolean;
}

interface TeamInfo {
  teamName: string;
  managerName: string;
  teamLogo: string | null;
}

interface TeamStats {
  id: string;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  weeks: TeamWeek[];
}

/** Values for each component before they are put on a 0–100 scale. */
type RawValues = Record<ComponentKey, number | null>;

interface ScoredTeam {
  stats: TeamStats;
  expectedWins: number;
  values: Record<ComponentKey, number | null>;
  score: number;
  rank: number;
  recordRank: number;
}

/** Scales `raw` to 0–100 by min–max; every team scores 50 when all values are equal. */
function minMaxScale(raw: Map<string, number>): Map<string, number> {
  const values = [...raw.values()];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const out = new Map<string, number>();
  for (const [id, v] of raw) {
    out.set(id, max === min ? 50 : ((v - min) / (max - min)) * 100);
  }
  return out;
}

function weightedAverage(values: Record<ComponentKey, number | null>): number {
  let total = 0;
  let weight = 0;
  for (const c of POWER_COMPONENTS) {
    const v = values[c.key];
    if (v === null) continue;
    total += v * c.weight;
    weight += c.weight;
  }
  return weight === 0 ? 0 : total / weight;
}

function formatRecord(wins: number, losses: number, ties: number): string {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
}

/** Collects each played regular-season team-week, plus the latest team names seen. */
function collectTeamWeeks(matchups: MatchupItem[]): {
  weeksByTeam: Map<string, TeamWeek[]>;
  info: Map<string, TeamInfo>;
  playedMatchups: MatchupItem[];
} {
  const weeksByTeam = new Map<string, TeamWeek[]>();
  const info = new Map<string, TeamInfo>();
  const playedMatchups: MatchupItem[] = [];

  for (const m of matchups) {
    const week = parseInt(m.week, 10);
    if (isNaN(week)) continue;
    if (!isRegularSeasonMatchup(m) || isUnplayedMatchup(m)) continue;
    playedMatchups.push(m);

    for (const side of ['a', 'b'] as const) {
      const other = side === 'a' ? 'b' : 'a';
      const id = m[`team_${side}_id`];
      const score = Number(m[`team_${side}_score`]);
      const oppScore = Number(m[`team_${other}_score`]);
      const starters = m[`team_${side}_starters`] ?? [];
      const bench = m[`team_${side}_bench`] ?? [];

      let actualLineup = 0;
      let optimalLineup = 0;
      const hasBench = starters.length > 0 && bench.length > 0;
      if (hasBench) {
        const report = computeStartSitReport(starters, bench);
        actualLineup = report.actualPoints;
        optimalLineup = report.optimalPoints;
      }

      const list = weeksByTeam.get(id) ?? [];
      list.push({
        week,
        score,
        result: score > oppScore ? 1 : score === oppScore ? 0.5 : 0,
        actualLineup,
        optimalLineup,
        hasBench,
      });
      weeksByTeam.set(id, list);
      info.set(id, {
        teamName: m[`team_${side}_team_name`],
        managerName: m[`team_${side}_display_name`],
        teamLogo: m[`team_${side}_team_logo`],
      });
    }
  }
  return { weeksByTeam, info, playedMatchups };
}

/** Scores and ranks every team using only the games played through `cutWeek`. */
function scoreCut(
  cutWeek: number,
  weeksByTeam: Map<string, TeamWeek[]>,
  playedMatchups: MatchupItem[],
): ScoredTeam[] {
  const stats: TeamStats[] = [];
  for (const [id, all] of weeksByTeam) {
    const weeks = all
      .filter((w) => w.week <= cutWeek)
      .sort((a, b) => a.week - b.week);
    if (weeks.length === 0) continue;
    stats.push({
      id,
      wins: weeks.filter((w) => w.result === 1).length,
      losses: weeks.filter((w) => w.result === 0).length,
      ties: weeks.filter((w) => w.result === 0.5).length,
      pf: weeks.reduce((sum, w) => sum + w.score, 0),
      weeks,
    });
  }

  // Expected wins (shown in a team's breakdown, not part of the score): each team's average
  // win total (a tie counts half) across every manager's schedule.
  const { matrix } = computeScheduleSwap(
    playedMatchups.filter((m) => parseInt(m.week, 10) <= cutWeek),
  );
  const expected: Record<string, number> = {};
  for (const [teamId, row] of matrix) {
    const totals = [...row.values()].map((r) => r.wins + 0.5 * r.ties);
    expected[teamId] = totals.reduce((a, b) => a + b, 0) / totals.length;
  }

  const raw = new Map<string, RawValues>();
  for (const t of stats) {
    const recent = t.weeks.slice(-FORM_WEEKS);
    const withBench = t.weeks.filter((w) => w.hasBench);
    const optimal = withBench.reduce((s, w) => s + w.optimalLineup, 0);
    const actual = withBench.reduce((s, w) => s + w.actualLineup, 0);
    raw.set(t.id, {
      record: ((t.wins + 0.5 * t.ties) / t.weeks.length) * 100,
      points: t.pf,
      form: recent.reduce((s, w) => s + w.score, 0) / recent.length,
      efficiency:
        withBench.length === 0
          ? null
          : optimal <= 0
            ? 1
            : Math.max(0, Math.min(1, actual / optimal)),
    });
  }

  // Record is already an absolute 0–100; the rest are scaled across the league.
  const scaled = new Map<ComponentKey, Map<string, number>>();
  for (const key of ['points', 'form', 'efficiency'] as const) {
    const present = new Map<string, number>();
    for (const [id, values] of raw) {
      const v = values[key];
      if (v !== null) present.set(id, v);
    }
    scaled.set(key, minMaxScale(present));
  }

  const scored = stats.map((t): ScoredTeam => {
    const r = raw.get(t.id)!;
    const values: Record<ComponentKey, number | null> = {
      record: r.record,
      points: scaled.get('points')!.get(t.id) ?? null,
      form: scaled.get('form')!.get(t.id) ?? null,
      efficiency: scaled.get('efficiency')!.get(t.id) ?? null,
    };
    return {
      stats: t,
      expectedWins: expected[t.id] ?? 0,
      values,
      score: weightedAverage(values),
      rank: 0,
      recordRank: 0,
    };
  });

  const winPoints = (t: ScoredTeam) => t.stats.wins + 0.5 * t.stats.ties;
  scored.sort(
    (a, b) =>
      b.score - a.score ||
      winPoints(b) - winPoints(a) ||
      b.stats.pf - a.stats.pf ||
      a.stats.id.localeCompare(b.stats.id),
  );
  scored.forEach((t, i) => {
    t.rank = i + 1;
  });

  [...scored]
    .sort(
      (a, b) =>
        winPoints(b) - winPoints(a) ||
        b.stats.pf - a.stats.pf ||
        a.stats.id.localeCompare(b.stats.id),
    )
    .forEach((t, i) => {
      t.recordRank = i + 1;
    });

  return scored;
}

function verdictFor(rank: number, recordRank: number): Verdict {
  const diff = recordRank - rank;
  if (diff >= VERDICT_THRESHOLD) return 'underrated';
  if (diff <= -VERDICT_THRESHOLD) return 'overrated';
  return 'on-the-mark';
}

function buildBlurb(
  verdict: Verdict,
  rank: number,
  recordRank: number,
  components: ComponentScore[],
): string {
  const gap = Math.abs(recordRank - rank);
  const lead =
    verdict === 'underrated'
      ? `Better than the record shows. They sit ${gap} spots higher here than in the standings.`
      : verdict === 'overrated'
        ? `The record is flattering. They rank ${gap} spots lower here than in the standings.`
        : 'Results and underlying strength tell the same story.';
  const available = components.filter(
    (c): c is ComponentScore & { value: number } => c.value !== null,
  );
  if (available.length === 0) return lead;
  const best = available.reduce((a, b) => (b.value > a.value ? b : a));
  const worst = available.reduce((a, b) => (b.value < a.value ? b : a));
  return `${lead} Strongest area: ${best.label.toLowerCase()}. Weakest: ${worst.label.toLowerCase()}.`;
}

/**
 * Builds the power rankings for every played regular-season week of a season.
 * `through(week)` ranks teams from the games played through that week; the
 * previous week's rankings (for movement and component changes) and the six-week
 * trend are derived from the preceding weeks.
 */
export function buildPowerRankings(matchups: MatchupItem[]): PowerRankings {
  const { weeksByTeam, info, playedMatchups } = collectTeamWeeks(matchups);
  const playedWeeks = [
    ...new Set([...weeksByTeam.values()].flat().map((w) => w.week)),
  ].sort((a, b) => a - b);

  const cuts = new Map<number, ScoredTeam[]>();
  for (const week of playedWeeks) {
    cuts.set(week, scoreCut(week, weeksByTeam, playedMatchups));
  }

  const through = (week: number): PowerRow[] => {
    const index = playedWeeks.indexOf(week);
    const current = cuts.get(week);
    if (index === -1 || !current) return [];

    const previous =
      index > 0
        ? new Map(cuts.get(playedWeeks[index - 1])!.map((t) => [t.stats.id, t]))
        : null;
    const trendWeeks = playedWeeks.slice(
      Math.max(0, index - (TREND_WEEKS - 1)),
      index + 1,
    );

    return current.map((t): PowerRow => {
      const id = t.stats.id;
      const prev = previous?.get(id) ?? null;
      const components = POWER_COMPONENTS.map((c): ComponentScore => {
        const value = t.values[c.key];
        const prevValue = prev ? prev.values[c.key] : null;
        return {
          key: c.key,
          label: c.label,
          weight: c.weight,
          value,
          delta:
            value !== null && prevValue !== null ? value - prevValue : null,
        };
      });
      const verdict = verdictFor(t.rank, t.recordRank);
      const trend = trendWeeks
        .map((w) => cuts.get(w)!.find((x) => x.stats.id === id)?.rank)
        .filter((r): r is number => r !== undefined);
      const games = t.stats.weeks.length;
      const teamInfo = info.get(id)!;

      return {
        teamId: id,
        teamName: teamInfo.teamName,
        managerName: teamInfo.managerName,
        teamLogo: teamInfo.teamLogo,
        wins: t.stats.wins,
        losses: t.stats.losses,
        ties: t.stats.ties,
        record: formatRecord(t.stats.wins, t.stats.losses, t.stats.ties),
        score: t.score,
        rank: t.rank,
        prevRank: prev ? prev.rank : null,
        movement: prev ? prev.rank - t.rank : 0,
        recordRank: t.recordRank,
        verdict,
        trend,
        components,
        expectedWins: t.expectedWins,
        expectedRecord: `${t.expectedWins.toFixed(1)}-${(games - t.expectedWins).toFixed(1)}`,
        blurb: buildBlurb(verdict, t.rank, t.recordRank, components),
      };
    });
  };

  return { playedWeeks, through };
}
