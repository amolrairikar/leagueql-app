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
