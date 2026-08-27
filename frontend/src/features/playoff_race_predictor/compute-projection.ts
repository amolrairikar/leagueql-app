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
  };
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
 * Each team's chance (0..1) of finishing in a top-`numPlayoffTeams` seed across
 * every possible result of the remaining *unpicked* matchups, treating each such
 * matchup as an equally likely 50/50 coin flip. Picked matchups are locked to
 * their result (folded into the fixed base), so odds are conditional on picks;
 * with no picks the base view enumerates all outcomes.
 *
 * Points-for is never simulated — it is fixed at its season-to-date value and
 * only breaks ties — so each matchup contributes a single win/loss bit and the
 * outcome space is exactly 2^N. Seeding per scenario uses the same rule as
 * {@link projectStandings} (wins desc, then points-for desc, then team id).
 *
 * Computed exactly by enumerating all 2^N combinations when N is small
 * ({@link MAX_EXACT_MATCHUPS}); otherwise estimated by Monte Carlo sampling.
 */
export function computePlayoffOdds(
  model: PredictorModel,
  picks: Picks,
): Map<string, number> {
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

  // Fixed tiebreak order (points-for desc, then id asc) => rank position; a
  // lower position outranks a higher one when win totals are equal.
  const tieRank = new Int32Array(n);
  ids
    .map((_, i) => i)
    .sort((x, y) => pf[y] - pf[x] || ids[x].localeCompare(ids[y]))
    .forEach((idx, pos) => {
      tieRank[idx] = pos;
    });

  const numPlayoff = model.numPlayoffTeams;
  const wins = new Int32Array(n);
  const counts = new Float64Array(n);

  // Tally, for the current `wins`, which teams land in a top-numPlayoff seed.
  const tallyScenario = (): void => {
    for (let i = 0; i < n; i++) {
      const wi = wins[i];
      const ri = tieRank[i];
      let above = 0;
      for (let j = 0; j < n; j++) {
        if (j === i) continue;
        const wj = wins[j];
        if (wj > wi || (wj === wi && tieRank[j] < ri)) above++;
      }
      if (above < numPlayoff) counts[i]++;
    }
  };

  let scenarios: number;
  if (numFree <= MAX_EXACT_MATCHUPS) {
    // Exact enumeration of all 2^numFree combinations (covers numFree === 0).
    scenarios = 2 ** numFree;
    for (let mask = 0; mask < scenarios; mask++) {
      wins.set(baseWins);
      for (let b = 0; b < numFree; b++) {
        wins[(mask >> b) & 1 ? freeB[b] : freeA[b]]++;
      }
      tallyScenario();
    }
  } else {
    // Monte Carlo: sample random outcomes with a fixed seed for determinism.
    scenarios = MONTE_CARLO_SAMPLES;
    const rand = mulberry32(0x9e3779b1);
    for (let s = 0; s < scenarios; s++) {
      wins.set(baseWins);
      for (let b = 0; b < numFree; b++) {
        wins[rand() < 0.5 ? freeA[b] : freeB[b]]++;
      }
      tallyScenario();
    }
  }

  const odds = new Map<string, number>();
  for (let i = 0; i < n; i++) odds.set(ids[i], counts[i] / scenarios);
  return odds;
}
