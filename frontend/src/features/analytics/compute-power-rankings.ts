import type { MatchupItem } from '@/components/api/types';

/** A single point on a manager's trend line for one week. */
export interface PowerPoint {
  week: number;
  /** 1-based league rank this week (1 = best), the value the chart plots. */
  rank: number;
  /** Blended power score through this week (~0–100), shown in the tooltip. */
  score: number;
}

/** One manager's power-score trend across the regular season. */
export interface PowerTeam {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
  /** Cumulative power score per week, ascending by week. */
  points: PowerPoint[];
}

export interface PowerRankingsData {
  /** All regular-season weeks with data, ascending (the shared x-axis). */
  weeks: number[];
  /** Managers sorted by latest rank (1 first), tie-broken on username. */
  teams: PowerTeam[];
}

/** Blend weights for the transparent power score (see FE-034). */
export const POWER_WEIGHTS = {
  allPlay: 0.5,
  pointsFor: 0.3,
  form: 0.2,
} as const;

/** Exponential decay applied per week back when weighting recent form. */
export const FORM_DECAY = 0.6;

/** A regular-season game is one with no playoff tier (`NONE` or absent). */
function isRegularSeason(m: MatchupItem): boolean {
  return !m.playoff_tier_type || m.playoff_tier_type === 'NONE';
}

interface TeamMeta {
  teamId: string;
  ownerUsername: string;
  teamName: string;
  teamLogo: string | null;
}

interface TeamState {
  /** Σ of all-play win fractions over weeks played against ≥1 opponent. */
  apfSum: number;
  apfCount: number;
  /** Σ of weekly scores over weeks played. */
  pfSum: number;
  pfCount: number;
  /** Chronological all-play win fractions (most recent last) for recent form. */
  apfHistory: number[];
  /** Whether this manager has played ≥1 regular-season game so far. */
  played: boolean;
}

/**
 * Recency-weighted average of a manager's all-play win fractions, scaled 0–100.
 * The most recent week carries weight 1 and each older week decays by
 * {@link FORM_DECAY}, so a hot/cold streak moves the value without a hard cutoff.
 */
function recencyForm(history: number[]): number {
  let weighted = 0;
  let weightSum = 0;
  for (let i = 0; i < history.length; i++) {
    const age = history.length - 1 - i;
    const weight = FORM_DECAY ** age;
    weighted += weight * history[i];
    weightSum += weight;
  }
  return weightSum > 0 ? (100 * weighted) / weightSum : 0;
}

/**
 * Build per-manager weekly power-score trend lines from a season's matchups
 * (FE-034). The point plotted at week W is cumulative through W and blends three
 * explainable, 0–100-normalized components:
 *
 *   powerScore(W) = 0.50·AP + 0.30·PF + 0.20·FORM
 *
 * where AP is the cumulative all-play win% (how often you'd beat the rest of the
 * league each week), PF is your cumulative scoring average as a share of the
 * league's best scorer, and FORM is a recency-weighted all-play win% (who's hot
 * now). Only regular-season games count; byes (a side with no finite score) and
 * self-matchup placeholders (`team_a_id === team_b_id`) are skipped. Each week the
 * blended scores are turned into 1-based ranks (1 = best) so the chart reads as a
 * bump chart; managers are returned sorted by their latest rank.
 */
export function computePowerRankings(
  matchups: MatchupItem[],
): PowerRankingsData {
  const meta = new Map<string, TeamMeta>();
  // week -> (teamId -> score that week)
  const weekScores = new Map<number, Map<string, number>>();

  for (const m of matchups) {
    if (!isRegularSeason(m)) continue;
    if (m.team_a_id === m.team_b_id) continue;
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);
    if (!Number.isFinite(aScore) || !Number.isFinite(bScore)) continue;
    const week = Number(m.week);
    if (!Number.isFinite(week)) continue;

    if (!weekScores.has(week)) weekScores.set(week, new Map());
    const wk = weekScores.get(week)!;
    for (const side of ['a', 'b'] as const) {
      const id = m[`team_${side}_id`];
      wk.set(id, Number(m[`team_${side}_score`]));
      // Names/logos can change across weeks; keep the latest seen.
      meta.set(id, {
        teamId: id,
        ownerUsername: m[`team_${side}_display_name`],
        teamName: m[`team_${side}_team_name`],
        teamLogo: m[`team_${side}_team_logo`],
      });
    }
  }

  const weeks = [...weekScores.keys()].sort((a, b) => a - b);
  if (weeks.length === 0) return { weeks: [], teams: [] };

  const state = new Map<string, TeamState>();
  const points = new Map<string, PowerPoint[]>();
  for (const id of meta.keys()) {
    state.set(id, {
      apfSum: 0,
      apfCount: 0,
      pfSum: 0,
      pfCount: 0,
      apfHistory: [],
      played: false,
    });
    points.set(id, []);
  }

  for (const week of weeks) {
    const wk = weekScores.get(week)!;
    const n = wk.size;

    // Fold this week's games into each manager's cumulative state.
    for (const [id, score] of wk) {
      const s = state.get(id)!;
      s.played = true;
      s.pfSum += score;
      s.pfCount += 1;
      // All-play needs ≥1 opponent that week (a lone team has no comparison).
      if (n >= 2) {
        let wins = 0;
        let ties = 0;
        for (const [otherId, otherScore] of wk) {
          if (otherId === id) continue;
          if (score > otherScore) wins += 1;
          else if (score === otherScore) ties += 1;
        }
        const apf = (wins + 0.5 * ties) / (n - 1);
        s.apfSum += apf;
        s.apfCount += 1;
        s.apfHistory.push(apf);
      }
    }

    // League-best cumulative scoring average so far, for the points-for share.
    let maxAvgPf = 0;
    for (const s of state.values()) {
      if (s.pfCount > 0) maxAvgPf = Math.max(maxAvgPf, s.pfSum / s.pfCount);
    }

    // Plot a point for every manager that has played at least once by this week.
    for (const [id, s] of state) {
      if (!s.played) continue;
      const ap = s.apfCount > 0 ? (100 * s.apfSum) / s.apfCount : 0;
      const avgPf = s.pfCount > 0 ? s.pfSum / s.pfCount : 0;
      const pf = maxAvgPf > 0 ? (100 * avgPf) / maxAvgPf : 0;
      const form = recencyForm(s.apfHistory);
      const score =
        POWER_WEIGHTS.allPlay * ap +
        POWER_WEIGHTS.pointsFor * pf +
        POWER_WEIGHTS.form * form;
      // rank is filled in below, once every manager's score for the week is known.
      points.get(id)!.push({ week, rank: 0, score });
    }
  }

  // Translate each week's raw scores into 1-based ranks (1 = best that week),
  // tie-broken on username so the bump-chart lines never overlap ambiguously.
  for (const week of weeks) {
    const atWeek: PowerPoint[] = [];
    const owner = new Map<PowerPoint, string>();
    for (const [id, pts] of points) {
      const p = pts.find((x) => x.week === week);
      if (p) {
        atWeek.push(p);
        owner.set(p, meta.get(id)!.ownerUsername);
      }
    }
    atWeek.sort(
      (a, b) => b.score - a.score || owner.get(a)!.localeCompare(owner.get(b)!),
    );
    atWeek.forEach((p, i) => {
      p.rank = i + 1;
    });
  }

  const teams: PowerTeam[] = [];
  for (const [id, pts] of points) {
    if (pts.length === 0) continue;
    teams.push({ ...meta.get(id)!, points: pts });
  }

  // Order managers by their latest rank (1 first); ranks are unique per week.
  teams.sort((a, b) => {
    const aFinal = a.points[a.points.length - 1].rank;
    const bFinal = b.points[b.points.length - 1].rank;
    return aFinal - bFinal || a.ownerUsername.localeCompare(b.ownerUsername);
  });

  return { weeks, teams };
}
