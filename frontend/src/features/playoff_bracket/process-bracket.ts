import {
  type BracketMatch,
  type Matchup,
  type WeeklyStandingItem,
} from './api-calls';

import { type Result } from '@/lib/result';

export interface BracketData {
  matches: BracketMatch[];
  matchups: Matchup[];
  recordMap: Record<string, string>;
  championshipWeek: number;
  maxRound: number;
}

export type BracketResult = Result<BracketData>;

// Championship week derived from actual playoff matchup data (handles week-17,
// week-18, etc.), falling back to the league's historical default when none is
// present.
export function championshipWeekFor(
  matchups: Matchup[],
  season: string,
): number {
  const playoffWeeks = matchups
    .filter((m) => m.playoff_tier_type && m.playoff_tier_type !== 'NONE')
    .map((m) => parseInt(m.week, 10))
    .filter((w) => !isNaN(w));
  return playoffWeeks.length > 0
    ? Math.max(...playoffWeeks)
    : parseInt(season, 10) < 2021
      ? 16
      : 17;
}

// Join the bracket, season matchups, and weekly standings into the shape the
// bracket renders: each bracket match paired with its matchup scores, plus the
// end-of-regular-season record per team.
export function processBracketData(
  bracketMatches: BracketMatch[],
  matchupsData: Matchup[],
  standingsData: WeeklyStandingItem[],
  season: string,
): BracketData {
  // Derive end-of-regular-season record per team from the last standings snapshot week
  const recordsByWeek: Record<number, Record<string, string>> = {};
  for (const s of standingsData) {
    const week = parseInt(s.snapshot_week, 10);
    if (!isNaN(week)) (recordsByWeek[week] ??= {})[s.team_id] = s.record;
  }
  const snapshotWeeks = Object.keys(recordsByWeek).map(Number);
  const recordMap =
    snapshotWeeks.length > 0 ? recordsByWeek[Math.max(...snapshotWeeks)] : {};

  const championshipWeek = championshipWeekFor(matchupsData, season);
  const maxRound =
    bracketMatches.length > 0
      ? Math.max(...bracketMatches.map((m) => m.round))
      : 0;

  // Match each bracket match with its corresponding matchup to get scores
  const matches = bracketMatches.map((bracketMatch) => {
    const week = championshipWeek - (maxRound - bracketMatch.round);
    const matchup = matchupsData.find(
      (m) =>
        m.season === bracketMatch.season &&
        parseInt(m.week, 10) === week &&
        ((m.team_a_id === bracketMatch.team_1_id &&
          m.team_b_id === bracketMatch.team_2_id) ||
          (m.team_a_id === bracketMatch.team_2_id &&
            m.team_b_id === bracketMatch.team_1_id)),
    );

    if (matchup) {
      // Match found, assign scores (handle team order)
      const team1IsA = matchup.team_a_id === bracketMatch.team_1_id;
      return {
        ...bracketMatch,
        team_1_score: team1IsA ? matchup.team_a_score : matchup.team_b_score,
        team_2_score: team1IsA ? matchup.team_b_score : matchup.team_a_score,
      };
    }

    // No matchup found, return bracket match without scores
    return bracketMatch;
  });

  return {
    matches,
    matchups: matchupsData,
    recordMap,
    championshipWeek,
    maxRound,
  };
}
