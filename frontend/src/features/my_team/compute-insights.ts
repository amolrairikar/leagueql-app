/**
 * Insight rule catalog (frontend/my-team) — pure, no I/O.
 *
 * NOT a flat library of prewritten strings. Each insight *type* is one catalog
 * entry with a predicate (does it apply to this team?), a severity score (for
 * ranking), and a `render` that fills ONE parameterized template from the team's
 * already-computed metrics. The engine runs every rule, keeps those that fire,
 * ranks them by score, and returns the top few — plus a hero verdict generated from
 * the single top-ranked theme. Rules guard on data availability so no half-filled
 * sentence renders.
 */
import type { TeamMetrics } from './compute-team-metrics';

export type Sentiment = 'good' | 'warn' | 'bad';

export interface Insight {
  id: string;
  sentiment: Sentiment;
  tag: string;
  headline: string;
  sentence: string;
  metric: { value: string; cap: string };
}

interface Rule {
  id: string;
  sentiment: Sentiment;
  applies: (m: TeamMetrics) => boolean;
  score: (m: TeamMetrics) => number;
  render: (m: TeamMetrics) => Omit<Insight, 'id' | 'sentiment'>;
}

const MAX_INSIGHTS = 6;

// ── Formatting helpers ──────────────────────────────────────────────────────────

export function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
}

function signed(n: number, dp = 1): string {
  return `${n >= 0 ? '+' : '-'}${Math.abs(n).toFixed(dp)}`;
}

function nameList(names: string[]): string {
  if (names.length === 0) return 'what you gave up';
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} & ${names[1]}`;
  return `${names.slice(0, -1).join(', ')} & ${names[names.length - 1]}`;
}

/** The team's most-negative trade, whether it landed in best or worst slot. */
function worstTrade(m: TeamMetrics) {
  const { best, worst } = m.trades;
  const candidates = [best, worst].filter(
    (t): t is NonNullable<typeof t> => t != null,
  );
  const min = candidates.reduce<(typeof candidates)[number] | null>(
    (acc, t) => (acc === null || t.net < acc.net ? t : acc),
    null,
  );
  return min && min.net < 0 ? min : null;
}

// ── Rule catalog ─────────────────────────────────────────────────────────────────

const RULES: Rule[] = [
  {
    id: 'unlucky',
    sentiment: 'warn',
    applies: (m) => m.luck !== null && m.luck <= -0.75,
    score: (m) => 60 + Math.abs(m.luck ?? 0) * 8,
    render: (m) => ({
      tag: 'Unlucky',
      headline:
        m.pfRank < m.seed
          ? `You're the best ${ordinal(m.seed)}-seed in the league`
          : `You've been unlucky`,
      sentence: `You have the ${ordinal(m.pfRank)}-most points but the ${ordinal(
        m.seed,
      )} seed — ${Math.abs(m.luck ?? 0).toFixed(1)} wins below expected.`,
      metric: { value: signed(m.luck ?? 0), cap: 'wins vs expected' },
    }),
  },
  {
    id: 'lucky',
    sentiment: 'warn',
    applies: (m) => m.luck !== null && m.luck >= 0.75,
    score: (m) => 45 + (m.luck ?? 0) * 6,
    render: (m) => ({
      tag: 'Riding luck',
      headline: `Your record flatters you`,
      sentence: `You're ${(m.luck ?? 0).toFixed(
        1,
      )} wins above expected — the schedule has been kind so far.`,
      metric: { value: signed(m.luck ?? 0), cap: 'wins vs expected' },
    }),
  },
  {
    id: 'best-trade',
    sentiment: 'good',
    applies: (m) => m.trades.best !== null && m.trades.best.net > 0,
    score: (m) => 35 + Math.min(m.trades.best?.net ?? 0, 60) * 0.6,
    render: (m) => {
      const t = m.trades.best!;
      return {
        tag: 'Trade win',
        headline: `The ${nameList(t.acquired)} deal is your best move`,
        sentence: `Since Week ${t.week}, ${nameList(
          t.acquired,
        )} has outscored ${nameList(
          t.gaveUp,
        )} by ${t.net.toFixed(1)} points — your best trade return.`,
        metric: { value: signed(t.net), cap: 'net points' },
      };
    },
  },
  {
    id: 'trade-regret',
    sentiment: 'bad',
    applies: (m) => worstTrade(m) !== null,
    score: (m) => 30 + Math.abs(worstTrade(m)?.net ?? 0) * 0.6,
    render: (m) => {
      const t = worstTrade(m)!;
      return {
        tag: 'Trade regret',
        headline: `The ${nameList(t.gaveUp)} trade has cost you`,
        sentence: `${nameList(t.gaveUp)} has outscored ${nameList(
          t.acquired,
        )} by ${Math.abs(t.net).toFixed(
          1,
        )} points since the Week ${t.week} deal.`,
        metric: { value: signed(t.net), cap: 'net points' },
      };
    },
  },
  {
    id: 'bench-leak',
    sentiment: 'bad',
    applies: (m) => m.efficiency !== null && m.efficiency < 0.94,
    score: (m) => 40 + m.pointsLeft * 0.15,
    render: (m) => ({
      tag: 'Leaving points on the bench',
      headline: `${m.pointsLeft.toFixed(0)} points left on your bench`,
      sentence: `Your lineup efficiency is ${(
        (m.efficiency ?? 0) * 100
      ).toFixed(1)}%${
        m.worstBenchWeek
          ? `; Week ${m.worstBenchWeek.week} alone left ${m.worstBenchWeek.pointsLeft.toFixed(
              0,
            )} on the bench`
          : ''
      }.`,
      metric: {
        value: `${((m.efficiency ?? 0) * 100).toFixed(1)}%`,
        cap: 'efficiency',
      },
    }),
  },
  {
    id: 'lineup-sharp',
    sentiment: 'good',
    applies: (m) => m.efficiency !== null && m.efficiency >= 0.97,
    score: (m) => 25 + (m.efficiency ?? 0) * 10,
    render: (m) => ({
      tag: 'Sharp lineups',
      headline: `You set near-optimal lineups`,
      sentence: `Your lineup efficiency is ${(
        (m.efficiency ?? 0) * 100
      ).toFixed(1)}% — you leave almost nothing on the bench.`,
      metric: {
        value: `${((m.efficiency ?? 0) * 100).toFixed(1)}%`,
        cap: 'efficiency',
      },
    }),
  },
  {
    id: 'draft-steal',
    sentiment: 'good',
    applies: (m) =>
      m.draft.bestPick !== null && (m.draft.bestPick.draft_rank_delta ?? 0) > 0,
    score: (m) => 28 + (m.draft.bestPick?.draft_rank_delta ?? 0),
    render: (m) => {
      const p = m.draft.bestPick!;
      const finish =
        p.actual_position_rank !== null
          ? ` — finished as ${p.position}${p.actual_position_rank}`
          : '';
      return {
        tag: 'Draft steal',
        headline: `${p.player_name ?? 'Your best pick'} won you the draft`,
        sentence: `Taken in Round ${p.round}${finish}, your best value pick by ${p.draft_rank_delta} spots.`,
        metric: {
          value: signed(p.draft_rank_delta ?? 0, 0),
          cap: 'rank delta',
        },
      };
    },
  },
  {
    id: 'draft-bust',
    sentiment: 'bad',
    applies: (m) =>
      m.draft.worstPick !== null &&
      (m.draft.worstPick.draft_rank_delta ?? 0) < 0,
    score: (m) => 24 + Math.abs(m.draft.worstPick?.draft_rank_delta ?? 0),
    render: (m) => {
      const p = m.draft.worstPick!;
      const finish =
        p.actual_position_rank !== null
          ? ` — finished as ${p.position}${p.actual_position_rank}`
          : '';
      return {
        tag: 'Draft bust',
        headline: `${p.player_name ?? 'Your worst pick'} hasn't paid off`,
        sentence: `Drafted in Round ${p.round}${finish}, your worst value pick by ${Math.abs(
          p.draft_rank_delta ?? 0,
        )} spots.`,
        metric: {
          value: signed(p.draft_rank_delta ?? 0, 0),
          cap: 'rank delta',
        },
      };
    },
  },
  {
    id: 'elite-scoring',
    sentiment: 'good',
    applies: (m) => m.pfRank <= 2 && m.numTeams >= 4,
    score: (m) => 32 - m.pfRank * 2,
    render: (m) => ({
      tag: 'Elite scoring',
      headline: `You're ${ordinal(m.pfRank)} in the league in scoring`,
      sentence: `${m.avgPf.toFixed(1)} points per week — one of the league's best offenses.`,
      metric: { value: m.avgPf.toFixed(1), cap: 'avg pts' },
    }),
  },
  {
    id: 'all-play-over',
    sentiment: 'good',
    applies: (m) => m.allPlayWinPct - m.winPct >= 0.1,
    score: (m) => 20 + (m.allPlayWinPct - m.winPct) * 30,
    render: (m) => ({
      tag: 'Beats the field',
      headline: `You beat more than just your schedule`,
      sentence: `Your all-play record is ${m.allPlayWins}-${m.allPlayLosses} (${(
        m.allPlayWinPct * 100
      ).toFixed(0)}%), better than your ${m.record} on the season.`,
      metric: {
        value: `${(m.allPlayWinPct * 100).toFixed(0)}%`,
        cap: 'all-play',
      },
    }),
  },
  {
    id: 'tough-schedule',
    sentiment: 'warn',
    applies: (m) => m.sos !== null && m.sosRank !== null && m.sosRank <= 2,
    score: (m) => 22 + (3 - (m.sosRank ?? 3)) * 4,
    render: (m) => ({
      tag: 'Tough schedule',
      headline:
        m.sosRank === 1
          ? `You've had the toughest schedule`
          : `You've had one of the toughest schedules`,
      sentence: `Your opponents win at a ${(m.sos ?? 0).toFixed(
        3,
      )} clip — ${m.sosRank === 1 ? 'the highest' : 'among the highest'} in the league.`,
      metric: { value: (m.sos ?? 0).toFixed(3), cap: 'opp win %' },
    }),
  },
  {
    id: 'hot-streak',
    sentiment: 'good',
    applies: (m) =>
      m.recentForm.length >= 3 &&
      m.recentForm.slice(0, 3).every((g) => g.result === 'W'),
    score: () => 26,
    render: () => ({
      tag: 'Heating up',
      headline: `You're on a winning streak`,
      sentence: `You've won each of your last 3 games and are peaking at the right time.`,
      metric: { value: 'W-W-W', cap: 'last 3' },
    }),
  },
  {
    id: 'cold-streak',
    sentiment: 'bad',
    applies: (m) =>
      m.recentForm.length >= 3 &&
      m.recentForm.slice(0, 3).every((g) => g.result === 'L'),
    score: () => 27,
    render: () => ({
      tag: 'Cooling off',
      headline: `You're in a losing skid`,
      sentence: `You've dropped each of your last 3 games at the worst possible time.`,
      metric: { value: 'L-L-L', cap: 'last 3' },
    }),
  },
];

/** Evaluate the catalog for a team: fired rules, ranked by severity, top few. */
export function computeInsights(m: TeamMetrics): Insight[] {
  return RULES.filter((r) => r.applies(m))
    .map((r) => ({ id: r.id, sentiment: r.sentiment, ...r.render(m) }))
    .sort((a, b) => {
      const ra = RULES.find((r) => r.id === a.id)!.score(m);
      const rb = RULES.find((r) => r.id === b.id)!.score(m);
      return rb - ra || a.id.localeCompare(b.id);
    })
    .slice(0, MAX_INSIGHTS);
}

/** A one-line hero verdict, generated from the team's top-ranked insight theme. */
export function heroVerdict(m: TeamMetrics, insights: Insight[]): string {
  const top = insights[0]?.id;
  switch (top) {
    case 'unlucky':
      return `A contender the standings are hiding: you have the ${ordinal(
        m.pfRank,
      )}-most points but sit ${ordinal(
        m.seed,
      )}. Your all-play record says you're better than your seed.`;
    case 'lucky':
      return `Sitting ${ordinal(
        m.seed,
      )} at ${m.record}, but the underlying numbers say the record is running ahead of the roster.`;
    case 'best-trade':
      return `You've been active on the trade market, and it's paying off — your roster is stronger than draft day left it.`;
    case 'bench-leak':
      return `The roster is good enough; the lineup card is the problem — you've left ${m.pointsLeft.toFixed(
        0,
      )} points on the bench this season.`;
    case 'elite-scoring':
      return `One of the league's best offenses at ${m.avgPf.toFixed(
        1,
      )} per week — you can win a shootout with anyone.`;
    case 'cold-streak':
      return `A rough stretch at the wrong time — ${m.record} on the season but reeling into the final weeks.`;
    case 'hot-streak':
      return `Peaking at the right time: ${m.record} and winning your last three heading toward the playoffs.`;
    default:
      return `${m.record}, ${ordinal(m.seed)} of ${m.numTeams} — a ${
        m.grade?.letter ?? '—'
      } season so far with room to climb.`;
  }
}
