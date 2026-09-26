import type { LeagueSettingsItem, MatchupItem } from '@/components/api/types';
import { isRegularSeason } from '@/features/schedule_swap/compute-schedule-swap';
import { isUnplayedMatchup } from '@/lib/matchups';

/**
 * The predictor projects a season's final standings from the user's picks of the
 * remaining regular-season games. It runs in two modes:
 * - `live`: a real in-progress season — the pickable games are the unplayed (0-0)
 *   regular-season weeks bounded by `regular_season_weeks`.
 * - `replay`: a completed season (demo) — the pickable games are the last three
 *   regular-season weeks, presented unpicked, with the baseline being records
 *   through the week before that window.
 *
 * Everything is computed from `MATCHUPS` alone: records, points-for (season-to-date,
 * used only as a tiebreaker), and team display fields.
 */
export type PredictorMode = 'live' | 'replay';

export interface PredictorTeam {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
}

/** A single pickable matchup, keyed uniquely within its week. */
export interface PickableMatchup {
  key: string;
  week: number;
  teamAId: string;
  teamBId: string;
}

export interface WeekGroup {
  week: number;
  matchups: PickableMatchup[];
}

interface BaseRecord {
  wins: number;
  losses: number;
  ties: number;
  pf: number;
}

/**
 * A team's regular-season scoring distribution, used to weight the win
 * probability of each remaining matchup. `std` is already resolved: a team's own
 * sample standard deviation when it has enough games, otherwise a league-wide
 * fallback (see {@link buildPredictorModel}).
 */
export interface TeamScoring {
  mean: number;
  std: number;
  games: number;
}

export interface PredictorModel {
  teams: Map<string, PredictorTeam>;
  /** Record + points-for entering the pickable window. */
  baseline: Map<string, BaseRecord>;
  /** Pickable weeks, ascending. */
  weeks: WeekGroup[];
  numPlayoffTeams: number;
  numPlayoffTeamsAssumed: boolean;
  regularSeasonWeeks: number;
  /** True once any postseason game has actually been played (gates the live tool). */
  hasPlayedPlayoffMatchup: boolean;
  /**
   * Per-team regular-season scoring distribution, used to weight each remaining
   * matchup's win probability. Absent (or missing a team) when there is no
   * scoring history to build it from — callers then treat the matchup as 50/50.
   */
  teamScoring?: Map<string, TeamScoring>;
}

/** Maps a matchup key to the picked winning team id. */
export type Picks = Record<string, string>;

export interface StandingRow {
  team: PredictorTeam;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  winPct: number;
  /** 1-based projected seed. */
  seed: number;
  inPlayoffs: boolean;
  /** Baseline seed minus projected seed: positive = moved up. */
  movement: number;
  clinched: boolean;
}

const emptyRecord = (): BaseRecord => ({ wins: 0, losses: 0, ties: 0, pf: 0 });

/** Sort by wins desc, then points-for desc, then team id for stability. */
function compareRecords(
  a: { wins: number; pf: number; id: string },
  b: { wins: number; pf: number; id: string },
): number {
  return b.wins - a.wins || b.pf - a.pf || a.id.localeCompare(b.id);
}

function maxRegularSeasonWeek(regMatchups: MatchupItem[]): number {
  return regMatchups.reduce((max, m) => Math.max(max, Number(m.week)), 0);
}

/**
 * Build the static projection inputs (teams, baseline records, pickable weeks) that
 * do not depend on the user's picks. Call once per data load; feed the result to
 * {@link projectStandings} and {@link recordEnteringWeek} as picks change.
 */
export function buildPredictorModel(
  matchups: MatchupItem[],
  settings: LeagueSettingsItem | null,
  mode: PredictorMode,
): PredictorModel {
  const teams = new Map<string, PredictorTeam>();
  for (const m of matchups) {
    teams.set(m.team_a_id, {
      teamId: m.team_a_id,
      ownerUsername: m.team_a_display_name,
      teamName: m.team_a_team_name,
      teamLogo: m.team_a_team_logo,
    });
    teams.set(m.team_b_id, {
      teamId: m.team_b_id,
      ownerUsername: m.team_b_display_name,
      teamName: m.team_b_team_name,
      teamLogo: m.team_b_team_logo,
    });
  }

  const regMatchupsAll = matchups.filter(isRegularSeason);
  const regularSeasonWeeks =
    settings?.regular_season_weeks ?? maxRegularSeasonWeek(regMatchupsAll);
  const numPlayoffTeams = settings?.num_playoff_teams ?? 6;
  const numPlayoffTeamsAssumed = settings
    ? settings.num_playoff_teams_assumed
    : true;

  const regMatchups = regMatchupsAll.filter(
    (m) => Number(m.week) <= regularSeasonWeeks,
  );
  const hasPlayedPlayoffMatchup = matchups.some(
    (m) => !isRegularSeason(m) && !isUnplayedMatchup(m),
  );

  const orderedRegWeeks = [
    ...new Set(regMatchups.map((m) => Number(m.week))),
  ].sort((a, b) => a - b);

  const pickableWeekNums =
    mode === 'live'
      ? [
          ...new Set(
            regMatchups.filter(isUnplayedMatchup).map((m) => Number(m.week)),
          ),
        ].sort((a, b) => a - b)
      : orderedRegWeeks.slice(-3);
  const pickableSet = new Set(pickableWeekNums);

  const weeks: WeekGroup[] = pickableWeekNums.map((week) => ({
    week,
    matchups: regMatchups
      .filter((m) => Number(m.week) === week)
      .map((m, i) => ({
        key: `${week}:${i}`,
        week,
        teamAId: m.team_a_id,
        teamBId: m.team_b_id,
      })),
  }));

  // Baseline = played regular-season games outside the pickable window.
  const baseline = new Map<string, BaseRecord>();
  for (const id of teams.keys()) baseline.set(id, emptyRecord());
  const ensure = (id: string): BaseRecord => {
    let rec = baseline.get(id);
    if (!rec) {
      rec = emptyRecord();
      baseline.set(id, rec);
    }
    return rec;
  };
  for (const m of regMatchups) {
    if (pickableSet.has(Number(m.week))) continue;
    if (isUnplayedMatchup(m)) continue;
    const a = ensure(m.team_a_id);
    const b = ensure(m.team_b_id);
    a.pf += Number(m.team_a_score);
    b.pf += Number(m.team_b_score);
    if (m.team_a_score > m.team_b_score) {
      a.wins++;
      b.losses++;
    } else if (m.team_b_score > m.team_a_score) {
      b.wins++;
      a.losses++;
    } else {
      a.ties++;
      b.ties++;
    }
  }

  return {
    teams,
    baseline,
    weeks,
    numPlayoffTeams,
    numPlayoffTeamsAssumed,
    regularSeasonWeeks,
    hasPlayedPlayoffMatchup,
    teamScoring: buildTeamScoring(regMatchups),
  };
}

/** Minimum games before a team's own standard deviation is trusted over the league's. */
const MIN_GAMES_FOR_OWN_STD = 3;
/** Standard deviations at or below this are treated as no spread (fall back to the league). */
const STD_EPSILON = 1e-9;

/**
 * Per-team regular-season scoring distribution built from played games only
 * (0-0 placeholders excluded). Each team's `mean` is its own average score, while
 * `std` is its own sample standard deviation once it has {@link MIN_GAMES_FOR_OWN_STD}
 * games with a non-trivial spread, and otherwise a shared league-wide standard
 * deviation (the pooled within-team residual std). Returns `undefined` when no games
 * have been played, so callers fall back to an even 50/50 matchup weight.
 */
function buildTeamScoring(
  playedRegMatchups: MatchupItem[],
): Map<string, TeamScoring> | undefined {
  const scores = new Map<string, number[]>();
  const add = (id: string, score: number): void => {
    const list = scores.get(id);
    if (list) list.push(score);
    else scores.set(id, [score]);
  };
  for (const m of playedRegMatchups) {
    if (isUnplayedMatchup(m)) continue;
    add(m.team_a_id, Number(m.team_a_score));
    add(m.team_b_id, Number(m.team_b_score));
  }
  if (scores.size === 0) return undefined;

  const means = new Map<string, number>();
  for (const [id, list] of scores) {
    means.set(id, list.reduce((a, b) => a + b, 0) / list.length);
  }

  // League-wide σ = pooled within-team residual std across every game score.
  let residualSq = 0;
  let residualDof = 0;
  for (const [id, list] of scores) {
    const mean = means.get(id)!;
    for (const s of list) residualSq += (s - mean) ** 2;
    residualDof += list.length - 1;
  }
  const leagueStd = residualDof > 0 ? Math.sqrt(residualSq / residualDof) : 0;

  const ownStd = (list: number[], mean: number): number => {
    if (list.length < 2) return 0;
    const variance =
      list.reduce((a, s) => a + (s - mean) ** 2, 0) / (list.length - 1);
    return Math.sqrt(variance);
  };

  const teamScoring = new Map<string, TeamScoring>();
  for (const [id, list] of scores) {
    const mean = means.get(id)!;
    const own = ownStd(list, mean);
    const std =
      list.length >= MIN_GAMES_FOR_OWN_STD && own > STD_EPSILON
        ? own
        : leagueStd;
    teamScoring.set(id, { mean, std, games: list.length });
  }
  return teamScoring;
}

/** Standard normal CDF via the Abramowitz & Stegun 7.1.26 erf approximation. */
function normalCdf(z: number): number {
  const sign = z < 0 ? -1 : 1;
  const x = Math.abs(z) / Math.SQRT2;
  const t = 1 / (1 + 0.3275911 * x);
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) *
      t +
      0.254829592) *
      t *
      Math.exp(-x * x);
  return 0.5 * (1 + sign * y);
}

/**
 * Probability that `aId` beats `bId` in a single game, from the two teams' scoring
 * distributions: with each score modeled as `N(mean, std)` and the teams
 * independent, the margin is `N(meanA - meanB, sqrt(stdA^2 + stdB^2))`, so the win
 * probability is `Φ((meanA - meanB) / σ_diff)`. Falls back to a coin flip (0.5) when
 * scoring data is missing for either team or the combined spread is ~0.
 */
function matchupWinProb(
  model: PredictorModel,
  aId: string,
  bId: string,
): number {
  const scoring = model.teamScoring;
  if (!scoring) return 0.5;
  const a = scoring.get(aId);
  const b = scoring.get(bId);
  if (!a || !b || a.games < 1 || b.games < 1) return 0.5;
  const sigma = Math.sqrt(a.std * a.std + b.std * b.std);
  if (sigma <= STD_EPSILON) return 0.5;
  return normalCdf((a.mean - b.mean) / sigma);
}

/** Total number of pickable matchups in the model. */
export function totalPickableMatchups(model: PredictorModel): number {
  return model.weeks.reduce((n, w) => n + w.matchups.length, 0);
}

/**
 * A team's record entering `week`: its baseline plus the results of the user's picks
 * in earlier pickable weeks only. A pick in `week` itself does not change this.
 */
export function recordEnteringWeek(
  model: PredictorModel,
  teamId: string,
  week: number,
  picks: Picks,
): { wins: number; losses: number; ties: number } {
  const base = model.baseline.get(teamId) ?? emptyRecord();
  const ties = base.ties;
  let wins = base.wins;
  let losses = base.losses;
  for (const group of model.weeks) {
    if (group.week >= week) break;
    for (const pm of group.matchups) {
      const winner = picks[pm.key];
      if (!winner) continue;
      if (pm.teamAId !== teamId && pm.teamBId !== teamId) continue;
      if (winner === teamId) wins++;
      else losses++;
    }
  }
  return { wins, losses, ties };
}

function computeClinched(
  model: PredictorModel,
  picks: Picks,
  projected: Map<string, BaseRecord>,
): Set<string> {
  const remaining = new Map<string, number>();
  for (const id of model.teams.keys()) remaining.set(id, 0);
  for (const group of model.weeks) {
    for (const pm of group.matchups) {
      if (picks[pm.key]) continue;
      remaining.set(pm.teamAId, (remaining.get(pm.teamAId) ?? 0) + 1);
      remaining.set(pm.teamBId, (remaining.get(pm.teamBId) ?? 0) + 1);
    }
  }
  const clinched = new Set<string>();
  for (const [id, rec] of projected) {
    const minWins = rec.wins;
    let canFinishAbove = 0;
    for (const [otherId, otherRec] of projected) {
      if (otherId === id) continue;
      const otherMax = otherRec.wins + (remaining.get(otherId) ?? 0);
      if (otherMax > minWins) canFinishAbove++;
    }
    if (canFinishAbove < model.numPlayoffTeams) clinched.add(id);
  }
  return clinched;
}

/**
 * Project the full standings from the current picks: baseline plus the result of
 * every picked matchup, sorted into seeds with movement vs. the baseline order and a
 * clinched flag (only while games remain unpicked).
 */
export function projectStandings(
  model: PredictorModel,
  picks: Picks,
): StandingRow[] {
  const projected = new Map<string, BaseRecord>();
  for (const [id, base] of model.baseline) projected.set(id, { ...base });

  for (const group of model.weeks) {
    for (const pm of group.matchups) {
      const winner = picks[pm.key];
      if (!winner) continue;
      const loser = pm.teamAId === winner ? pm.teamBId : pm.teamAId;
      const w = projected.get(winner);
      const l = projected.get(loser);
      if (w) w.wins++;
      if (l) l.losses++;
    }
  }

  const baselineOrder = [...model.baseline.entries()]
    .map(([id, r]) => ({ id, ...r }))
    .sort(compareRecords);
  const baselineSeed = new Map(baselineOrder.map((r, i) => [r.id, i]));

  const clinched = computeClinched(model, picks, projected);
  const anyRemaining = totalPickableMatchups(model) > Object.keys(picks).length;

  return [...projected.entries()]
    .map(([id, r]) => ({ id, ...r }))
    .sort(compareRecords)
    .map((r, i) => {
      const games = r.wins + r.losses + r.ties;
      const inPlayoffs = i < model.numPlayoffTeams;
      return {
        team: model.teams.get(r.id)!,
        wins: r.wins,
        losses: r.losses,
        ties: r.ties,
        pf: r.pf,
        winPct: games > 0 ? (r.wins + 0.5 * r.ties) / games : 0,
        seed: i + 1,
        inPlayoffs,
        movement: (baselineSeed.get(r.id) ?? i) - i,
        clinched: inPlayoffs && anyRemaining && clinched.has(r.id),
      };
    });
}

/**
 * Above this many unpicked matchups the outcome space (2^N) is too large to
 * enumerate exactly on every pick, so odds fall back to Monte Carlo sampling.
 * A ~12-team league's realistic race window (the last ~3 weeks, 18 matchups)
 * stays comfortably under this bound and is computed exactly.
 */
const MAX_EXACT_MATCHUPS = 20;
/** Random outcomes drawn when the space is too large to enumerate exactly. */
const MONTE_CARLO_SAMPLES = 50_000;

/** Small seeded PRNG so the sampling path is deterministic (and testable). */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Each team's probability (0..1) of finishing in *each* seed across every possible
 * result of the remaining *unpicked* matchups. Each such matchup is weighted by the
 * probability that each team wins it, derived from the two teams' scoring
 * distributions via {@link matchupWinProb} (a coin flip when scoring history is
 * absent). The returned map gives every team a length-`n` array where index `k` is
 * the chance of finishing in seed `k + 1` (1-based). Picked matchups are locked to
 * their result (folded into the fixed base), so the distribution is conditional on
 * picks; with no picks the base view enumerates all outcomes.
 *
 * Points-for is never simulated — it is fixed at its season-to-date value and
 * only breaks ties — so each matchup contributes a single win/loss bit and the
 * outcome space is exactly 2^N. Seeding per scenario uses the same rule as
 * {@link projectStandings} (wins desc, then points-for desc, then team id), which
 * assigns every team a unique rank, so each team's array sums to exactly 1 (to ~1
 * under sampling).
 *
 * Computed exactly by enumerating all 2^N combinations — each weighted by its
 * probability — when N is small ({@link MAX_EXACT_MATCHUPS}); otherwise estimated by
 * Monte Carlo sampling that draws each matchup at its win probability.
 */
export function computeSeedProbabilities(
  model: PredictorModel,
  picks: Picks,
): Map<string, number[]> {
  const ids = [...model.teams.keys()];
  const n = ids.length;
  const index = new Map(ids.map((id, i) => [id, i]));

  // Fixed base: baseline wins plus every picked result; points-for is fixed.
  const baseWins = new Int32Array(n);
  const pf = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const base = model.baseline.get(ids[i]) ?? emptyRecord();
    baseWins[i] = base.wins;
    pf[i] = base.pf;
  }
  // Unpicked matchups become free win/loss bits; picked ones lock into baseWins.
  // pFree[b] is the probability that freeA[b] (team A) wins that matchup.
  const freeA: number[] = [];
  const freeB: number[] = [];
  const pFree: number[] = [];
  for (const group of model.weeks) {
    for (const pm of group.matchups) {
      const winner = picks[pm.key];
      if (winner) {
        baseWins[index.get(winner)!]++;
      } else {
        freeA.push(index.get(pm.teamAId)!);
        freeB.push(index.get(pm.teamBId)!);
        pFree.push(matchupWinProb(model, pm.teamAId, pm.teamBId));
      }
    }
  }
  const numFree = freeA.length;

  // Fixed tiebreak order (points-for desc, then id asc) => rank position; a
  // lower position outranks a higher one when win totals are equal.
  const tieRank = new Int32Array(n);
  ids
    .map((_, i) => i)
    .sort((x, y) => pf[y] - pf[x] || ids[x].localeCompare(ids[y]))
    .forEach((idx, pos) => {
      tieRank[idx] = pos;
    });

  const wins = new Int32Array(n);
  // Row-major team × seed histogram: seedCounts[i * n + rank] for finishing rank.
  const seedCounts = new Float64Array(n * n);

  // Tally each team's exact finishing seed (rank) for the current `wins`, adding
  // this scenario's probability weight (1 per sample on the Monte Carlo path).
  const tallyScenario = (weight: number): void => {
    for (let i = 0; i < n; i++) {
      const wi = wins[i];
      const ri = tieRank[i];
      let above = 0;
      for (let j = 0; j < n; j++) {
        if (j === i) continue;
        const wj = wins[j];
        if (wj > wi || (wj === wi && tieRank[j] < ri)) above++;
      }
      seedCounts[i * n + above] += weight;
    }
  };

  // Total accumulated weight to normalize by: the summed combination weights on the
  // exact path (analytically 1), or the sample count under Monte Carlo.
  let norm: number;
  if (numFree <= MAX_EXACT_MATCHUPS) {
    // Exact enumeration of all 2^numFree combinations (covers numFree === 0), each
    // weighted by the product of its per-matchup win probabilities.
    const combos = 2 ** numFree;
    let totalWeight = 0;
    for (let mask = 0; mask < combos; mask++) {
      wins.set(baseWins);
      let weight = 1;
      for (let b = 0; b < numFree; b++) {
        if ((mask >> b) & 1) {
          wins[freeB[b]]++;
          weight *= 1 - pFree[b];
        } else {
          wins[freeA[b]]++;
          weight *= pFree[b];
        }
      }
      totalWeight += weight;
      tallyScenario(weight);
    }
    norm = totalWeight;
  } else {
    // Monte Carlo: draw each matchup at its win probability with a fixed seed.
    const samples = MONTE_CARLO_SAMPLES;
    const rand = mulberry32(0x9e3779b1);
    for (let s = 0; s < samples; s++) {
      wins.set(baseWins);
      for (let b = 0; b < numFree; b++) {
        wins[rand() < pFree[b] ? freeA[b] : freeB[b]]++;
      }
      tallyScenario(1);
    }
    norm = samples;
  }

  const probs = new Map<string, number[]>();
  for (let i = 0; i < n; i++) {
    const dist = new Array<number>(n);
    for (let k = 0; k < n; k++) dist[k] = seedCounts[i * n + k] / norm;
    probs.set(ids[i], dist);
  }
  return probs;
}

/**
 * Each team's chance (0..1) of finishing in a top-`numPlayoffTeams` seed across
 * every possible result of the remaining *unpicked* matchups — the sum of the
 * team's top-`numPlayoffTeams` seed probabilities from
 * {@link computeSeedProbabilities}, so the two views are always consistent.
 */
export function computePlayoffOdds(
  model: PredictorModel,
  picks: Picks,
): Map<string, number> {
  const seedProbs = computeSeedProbabilities(model, picks);
  const numPlayoff = model.numPlayoffTeams;
  const odds = new Map<string, number>();
  for (const [id, dist] of seedProbs) {
    let sum = 0;
    for (let k = 0; k < numPlayoff && k < dist.length; k++) sum += dist[k];
    odds.set(id, sum);
  }
  return odds;
}

export type ClinchCategory = 'win-and-in' | 'must-win' | 'controls-destiny';

export interface TieMargin {
  rival: PredictorTeam;
  /** team.pf − rival.pf: positive = the team leads by this many points-for. */
  gap: number;
}

export interface ClinchScenario {
  team: PredictorTeam;
  category: ClinchCategory;
  /** The team's next un-picked opponent (the decisive game), if any. */
  opponent: PredictorTeam | null;
  /** Rivals whose same-record tie could decide the seat, with the current PF gap. */
  tieMargins: TieMargin[];
}

export interface ClinchScenarios {
  scenarios: ClinchScenario[];
  numPlayoffTeams: number;
  numPlayoffTeamsAssumed: boolean;
}

/**
 * Plain-language clinching scenarios for teams still in contention: who clinches with
 * a win ("win-and-in"), is eliminated with a loss ("must-win"), or both
 * ("controls-destiny") in their next un-picked game. Computed exactly over the same
 * enumeration of un-picked outcomes as {@link computePlayoffOdds} and conditional on
 * the user's picks (a team's decisive game is its earliest un-picked matchup).
 *
 * Tiebreaks are handled rigorously: because points-for keeps accruing in the games
 * still to play, a same-record tie is never assumed decided. A berth therefore counts
 * as clinched only when record alone secures it, and clinched/eliminated teams are
 * omitted here (the standings convey them). When a listed team's seat can come down to
 * a same-record tie, the current points-for gap to each rival it must hold off is
 * attached as a {@link TieMargin}.
 *
 * Returns `null` when the un-picked space is too large to enumerate exactly (guarantees
 * can't be proven by sampling) or when no contending team has a decisive next game.
 */
export function computeClinchScenarios(
  model: PredictorModel,
  picks: Picks,
): ClinchScenarios | null {
  const ids = [...model.teams.keys()];
  const n = ids.length;
  const index = new Map(ids.map((id, i) => [id, i]));

  // Fixed base: baseline wins plus every picked result; points-for is season-to-date.
  const baseWins = new Int32Array(n);
  const pf = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const base = model.baseline.get(ids[i]) ?? emptyRecord();
    baseWins[i] = base.wins;
    pf[i] = base.pf;
  }

  // Un-picked matchups become free win/loss bits (in ascending week order).
  const freeA: number[] = [];
  const freeB: number[] = [];
  for (const group of model.weeks) {
    for (const pm of group.matchups) {
      const winner = picks[pm.key];
      if (winner) {
        baseWins[index.get(winner)!]++;
      } else {
        freeA.push(index.get(pm.teamAId)!);
        freeB.push(index.get(pm.teamBId)!);
      }
    }
  }
  const numFree = freeA.length;
  if (numFree === 0 || numFree > MAX_EXACT_MATCHUPS) return null;

  // Each team's next un-picked game = the earliest free bit it appears in.
  const nextBit = new Int32Array(n).fill(-1);
  const nextOpp = new Int32Array(n).fill(-1);
  for (let b = 0; b < numFree; b++) {
    if (nextBit[freeA[b]] === -1) {
      nextBit[freeA[b]] = b;
      nextOpp[freeA[b]] = freeB[b];
    }
    if (nextBit[freeB[b]] === -1) {
      nextBit[freeB[b]] = b;
      nextOpp[freeB[b]] = freeA[b];
    }
  }

  const numPlayoff = model.numPlayoffTeams;

  // Per-team accumulators over every 2^numFree win/loss combination.
  const inAll = new Uint8Array(n).fill(1); // record-guaranteed in every combo (clinched)
  const outAll = new Uint8Array(n).fill(1); // out in every combo (eliminated)
  const winCount = new Int32Array(n);
  const winInAll = new Uint8Array(n).fill(1);
  const winOutCount = new Int32Array(n);
  const loseCount = new Int32Array(n);
  const loseOutAll = new Uint8Array(n).fill(1);
  const loseOutCount = new Int32Array(n);
  const winTieRivals: Set<number>[] = Array.from(
    { length: n },
    () => new Set(),
  );
  const loseTieRivals: Set<number>[] = Array.from(
    { length: n },
    () => new Set(),
  );

  const wins = new Int32Array(n);
  const total = 2 ** numFree;
  for (let mask = 0; mask < total; mask++) {
    wins.set(baseWins);
    for (let b = 0; b < numFree; b++) {
      wins[(mask >> b) & 1 ? freeB[b] : freeA[b]]++;
    }
    for (let i = 0; i < n; i++) {
      const wi = wins[i];
      let strictlyBetter = 0;
      let tied = 0;
      for (let j = 0; j < n; j++) {
        if (j === i) continue;
        if (wins[j] > wi) strictlyBetter++;
        else if (wins[j] === wi) tied++;
      }
      const seats = numPlayoff - strictlyBetter;
      const isOut = seats <= 0;
      const isIn = !isOut && tied + 1 <= seats;
      const isTie = !isOut && !isIn;
      if (!isIn) inAll[i] = 0;
      if (!isOut) outAll[i] = 0;

      const nb = nextBit[i];
      if (nb === -1) continue;
      const iWon = (mask >> nb) & 1 ? freeB[nb] === i : freeA[nb] === i;
      if (iWon) {
        winCount[i]++;
        if (!isIn) winInAll[i] = 0;
        if (isOut) winOutCount[i]++;
        if (isTie) {
          for (let j = 0; j < n; j++) {
            if (j !== i && wins[j] === wi) winTieRivals[i].add(j);
          }
        }
      } else {
        loseCount[i]++;
        if (!isOut) loseOutAll[i] = 0;
        if (isOut) loseOutCount[i]++;
        if (isTie) {
          for (let j = 0; j < n; j++) {
            if (j !== i && wins[j] === wi) loseTieRivals[i].add(j);
          }
        }
      }
    }
  }

  const scenarios: ClinchScenario[] = [];
  for (let i = 0; i < n; i++) {
    if (inAll[i] || outAll[i]) continue; // clinched / eliminated → shown in the standings
    if (nextBit[i] === -1) continue;
    const winClinch = winCount[i] > 0 && winInAll[i] === 1;
    const lossElim = loseCount[i] > 0 && loseOutAll[i] === 1;
    if (!winClinch && !lossElim) continue;

    let category: ClinchCategory;
    let rivals: Set<number>;
    if (winClinch && lossElim) {
      category = 'controls-destiny';
      rivals = new Set(); // clean both ways — no tiebreak needed
    } else if (winClinch) {
      category = 'win-and-in';
      // Attach margins only when a loss is purely tiebreak-dependent (never out).
      rivals = loseOutCount[i] === 0 ? loseTieRivals[i] : new Set();
    } else {
      category = 'must-win';
      // Attach margins only when a win is purely tiebreak-dependent (never out).
      rivals = winOutCount[i] === 0 ? winTieRivals[i] : new Set();
    }

    const tieMargins: TieMargin[] = [...rivals]
      .map((j) => ({ rival: model.teams.get(ids[j])!, gap: pf[i] - pf[j] }))
      .sort((a, b) => a.gap - b.gap);

    scenarios.push({
      team: model.teams.get(ids[i])!,
      category,
      opponent:
        nextOpp[i] >= 0 ? (model.teams.get(ids[nextOpp[i]]) ?? null) : null,
      tieMargins,
    });
  }

  if (scenarios.length === 0) return null;

  const catOrder: Record<ClinchCategory, number> = {
    'controls-destiny': 0,
    'win-and-in': 1,
    'must-win': 2,
  };
  scenarios.sort(
    (a, b) =>
      catOrder[a.category] - catOrder[b.category] ||
      (model.baseline.get(b.team.teamId)?.pf ?? 0) -
        (model.baseline.get(a.team.teamId)?.pf ?? 0),
  );

  return {
    scenarios,
    numPlayoffTeams: model.numPlayoffTeams,
    numPlayoffTeamsAssumed: model.numPlayoffTeamsAssumed,
  };
}
