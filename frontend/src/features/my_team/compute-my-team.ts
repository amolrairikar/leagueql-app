import type { LeagueSettingsItem, MatchupItem } from '@/components/api/types';
import type { DraftPickItem } from '@/features/draft_grades/api-calls';
import { computeStartSitReport } from '@/features/lineup_efficiency/compute-lineup-efficiency';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import { buildMatchupPreview } from '@/features/matchups/compute-preview';
import {
  buildPredictorModel,
  computePlayoffOdds,
} from '@/features/playoff_race_predictor/compute-projection';
import { isRegularSeason } from '@/features/schedule_swap/compute-schedule-swap';
import {
  AWARD_DEFS,
  computeWeeklyAwards,
} from '@/features/weekly_awards/compute-awards';
import { isUnplayedMatchup } from '@/lib/matchups';

export type GameResult = 'W' | 'L' | 'T';

/** A team in the current season, as offered by the claim picker. */
export interface TeamOption {
  teamId: string;
  /** Raw platform owner id (what `PUT /me` stores). */
  ownerId: string;
  teamName: string;
  ownerUsername: string;
  teamLogo: string | null;
}

export interface TeamSummary extends TeamOption {
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  /** Points against (regular season). */
  pa: number;
  /** 1-based rank by wins, then points for (regular season). */
  rank: number;
}

export interface GameScore {
  result: GameResult;
  points: number;
  oppPoints: number;
  /** points − oppPoints. */
  margin: number;
}

export interface Meeting extends GameScore {
  season: string;
  week: number;
}

export interface ThisWeekMatchup {
  opponent: TeamSummary;
  projMine: number | null;
  projOpp: number | null;
  winProbMine: number;
  winProbOpp: number;
  /** All-time head-to-head from the claimed team's perspective, every season. */
  h2h: { wins: number; losses: number; ties: number };
  lastMeeting: Meeting | null;
  /** Opponent's last (up to) 3 played results this season, oldest first. */
  opponentLast3: GameResult[];
}

export interface Efficiency {
  /** Season-long actual ÷ optimal starter points (0..1); null with no lineup data. */
  seasonPct: number | null;
  /** Points left on the bench in last week's game; null when unavailable. */
  lastWeekPointsLeft: number | null;
}

export interface AwardsSummary {
  /** Award labels the team won last week. */
  lastWeek: string[];
  /** Highest Score awards this season (through last week). */
  highestScoreCount: number;
}

export interface InSeasonView {
  kind: 'in-season';
  season: string;
  team: TeamSummary;
  currentWeek: number;
  lastWeek: number | null;
  lastWeekGame: GameScore | null;
  /** Current playoff odds 0..1. */
  playoffOdds: number;
  /** Change in odds since before last week's games (0..1 points); null when unavailable. */
  playoffOddsChange: number | null;
  efficiency: Efficiency;
  matchup: ThisWeekMatchup | null;
  awards: AwardsSummary;
  topDraftPicks: TopDraftPick[];
}

export interface OffseasonView {
  kind: 'offseason';
  season: string;
  team: TeamSummary;
  /** Final placement, when the season's standings carry one. */
  finalRank: number | null;
  champion: boolean;
  /** Most consecutive wins this season (regular season and playoffs, in week order). */
  longestWinStreak: number;
  efficiency: Efficiency;
  awards: AwardsSummary;
  topDraftPicks: TopDraftPick[];
}

/** One of the claimed team's most valuable draft picks (by VORP). */
export interface TopDraftPick {
  playerName: string;
  position: string;
  round: number;
  roundPick: number;
  overallPick: number;
  /** Winning bid for an auction draft; null for a snake draft. */
  bid: number | null;
  vorp: number;
  totalPoints: number | null;
}

export type MyTeamView = InSeasonView | OffseasonView;

export interface MyTeamInput {
  /** Matchups for every loaded season. */
  matchups: MatchupItem[];
  standings: ManagerStandingsItem[];
  migrationMapping: Map<string, string>;
  /** League settings for the current season, if available. */
  settings: LeagueSettingsItem | null;
  /** The current (latest) season. */
  season: string;
  /** The current season's draft picks (empty when unavailable). */
  draftPicks: DraftPickItem[];
}

const wk = (m: MatchupItem): number => Number(m.week);

const TOP_DRAFT_PICKS = 3;

/**
 * The team's top draft picks by value over replacement, highest first. Picks with no
 * VORP (kickers, D/ST, players with no scoring data) are excluded.
 */
export function topDraftPicks(
  picks: DraftPickItem[],
  teamId: string,
  n = TOP_DRAFT_PICKS,
): TopDraftPick[] {
  return picks
    .filter((p) => String(p.team_id) === teamId && p.vorp != null)
    .sort(
      (a, b) =>
        b.vorp! - a.vorp! || a.overall_pick_number - b.overall_pick_number,
    )
    .slice(0, n)
    .map((p) => ({
      playerName: p.player_name ?? `Player ${p.player_id}`,
      position: p.position,
      round: p.round,
      roundPick: p.round_pick_number,
      overallPick: p.overall_pick_number,
      bid: p.is_auction ? p.bid_amount : null,
      vorp: p.vorp!,
      totalPoints: p.total_points,
    }));
}

function involves(m: MatchupItem, teamId: string): boolean {
  return m.team_a_id === teamId || m.team_b_id === teamId;
}

/** The claimed team's side of a played game. */
function scoreFor(m: MatchupItem, teamId: string): GameScore {
  const mineA = m.team_a_id === teamId;
  const points = Number(mineA ? m.team_a_score : m.team_b_score);
  const oppPoints = Number(mineA ? m.team_b_score : m.team_a_score);
  const result: GameResult =
    points > oppPoints ? 'W' : points < oppPoints ? 'L' : 'T';
  return { result, points, oppPoints, margin: points - oppPoints };
}

/** Every team in the season's matchups, ordered by team id. */
export function listSeasonTeams(
  matchups: MatchupItem[],
  season: string,
): TeamOption[] {
  const teams = new Map<string, TeamOption>();
  for (const m of matchups) {
    if (m.season !== season) continue;
    for (const side of ['a', 'b'] as const) {
      const id = side === 'a' ? m.team_a_id : m.team_b_id;
      if (teams.has(id)) continue;
      teams.set(id, {
        teamId: id,
        ownerId: String(
          side === 'a' ? m.team_a_primary_owner_id : m.team_b_primary_owner_id,
        ),
        teamName: side === 'a' ? m.team_a_team_name : m.team_b_team_name,
        ownerUsername:
          side === 'a' ? m.team_a_display_name : m.team_b_display_name,
        teamLogo: side === 'a' ? m.team_a_team_logo : m.team_b_team_logo,
      });
    }
  }
  return [...teams.values()].sort(
    (a, b) =>
      Number(a.teamId) - Number(b.teamId) || a.teamId.localeCompare(b.teamId),
  );
}

/**
 * The claimed owner's team this season, matching owners through the platform-migration
 * mapping on both sides; null when the owner has no team this season.
 */
export function resolveClaimedTeam(
  teams: TeamOption[],
  ownerId: string | null,
  migrationMapping: Map<string, string>,
): TeamOption | null {
  if (!ownerId) return null;
  const remap = (id: string) => migrationMapping.get(id) ?? id;
  const target = remap(ownerId);
  return teams.find((t) => remap(t.ownerId) === target) ?? null;
}

/** Regular-season records for every team, ranked by wins then points for. */
function seasonRecords(
  seasonMatchups: MatchupItem[],
  teams: TeamOption[],
): Map<string, TeamSummary> {
  const acc = new Map(
    teams.map((t) => [
      t.teamId,
      { ...t, wins: 0, losses: 0, ties: 0, pf: 0, pa: 0 },
    ]),
  );
  for (const m of seasonMatchups) {
    if (!isRegularSeason(m) || isUnplayedMatchup(m)) continue;
    for (const id of [m.team_a_id, m.team_b_id]) {
      const row = acc.get(id);
      if (!row) continue;
      const g = scoreFor(m, id);
      row.pf += g.points;
      row.pa += g.oppPoints;
      if (g.result === 'W') row.wins++;
      else if (g.result === 'L') row.losses++;
      else row.ties++;
    }
  }
  const ranked = [...acc.values()].sort(
    (a, b) =>
      b.wins - a.wins || b.pf - a.pf || a.teamId.localeCompare(b.teamId),
  );
  return new Map(ranked.map((r, i) => [r.teamId, { ...r, rank: i + 1 }]));
}

function computeEfficiency(
  seasonMatchups: MatchupItem[],
  teamId: string,
  lastWeek: number | null,
): Efficiency {
  let actual = 0;
  let optimal = 0;
  let lastWeekPointsLeft: number | null = null;
  for (const m of seasonMatchups) {
    if (!involves(m, teamId) || isUnplayedMatchup(m)) continue;
    const mineA = m.team_a_id === teamId;
    const starters = (mineA ? m.team_a_starters : m.team_b_starters) ?? [];
    const bench = (mineA ? m.team_a_bench : m.team_b_bench) ?? [];
    if (starters.length === 0) continue;
    const report = computeStartSitReport(starters, bench);
    if (!report.hasBenchData) continue;
    if (wk(m) === lastWeek) lastWeekPointsLeft = report.pointsLeft;
    if (!isRegularSeason(m)) continue;
    actual += report.actualPoints;
    optimal += report.optimalPoints;
  }
  return {
    seasonPct: optimal > 0 ? actual / optimal : null,
    lastWeekPointsLeft,
  };
}

/**
 * The team's longest run of consecutive wins in the season's played games (regular
 * season and playoffs) in week order; a loss or a tie ends a run.
 */
export function longestWinStreak(
  seasonMatchups: MatchupItem[],
  teamId: string,
): number {
  let best = 0;
  let run = 0;
  const games = seasonMatchups
    .filter((m) => involves(m, teamId) && !isUnplayedMatchup(m))
    .sort((a, b) => wk(a) - wk(b));
  for (const m of games) {
    run = scoreFor(m, teamId).result === 'W' ? run + 1 : 0;
    best = Math.max(best, run);
  }
  return best;
}

function computeAwards(
  seasonMatchups: MatchupItem[],
  teamId: string,
  lastWeek: number | null,
): AwardsSummary {
  const played = seasonMatchups.filter((m) => !isUnplayedMatchup(m));
  if (lastWeek == null || played.length === 0) {
    return { lastWeek: [], highestScoreCount: 0 };
  }
  const data = computeWeeklyAwards(played, lastWeek);
  const tallyRow = data.tally.find((r) => r.teamId === teamId);
  return {
    lastWeek: AWARD_DEFS.filter(
      (d) => data.awards[d.key]?.teamId === teamId,
    ).map((d) => d.label),
    highestScoreCount: tallyRow?.counts.highest ?? 0,
  };
}

function oddsFor(
  seasonMatchups: MatchupItem[],
  settings: LeagueSettingsItem | null,
  teamId: string,
): number {
  const model = buildPredictorModel(seasonMatchups, settings, 'live');
  return computePlayoffOdds(model, {}).get(teamId) ?? 0;
}

function headToHead(
  allMatchups: MatchupItem[],
  migrationMapping: Map<string, string>,
  myOwner: string,
  oppOwner: string,
): Pick<ThisWeekMatchup, 'h2h' | 'lastMeeting'> {
  const remap = (id: string) => migrationMapping.get(id) ?? id;
  const me = remap(myOwner);
  const opp = remap(oppOwner);
  const h2h = { wins: 0, losses: 0, ties: 0 };
  let lastMeeting: Meeting | null = null;
  for (const m of allMatchups) {
    if (isUnplayedMatchup(m)) continue;
    const a = remap(String(m.team_a_primary_owner_id));
    const b = remap(String(m.team_b_primary_owner_id));
    let mineId: string;
    if (a === me && b === opp) mineId = m.team_a_id;
    else if (a === opp && b === me) mineId = m.team_b_id;
    else continue;
    const g = scoreFor(m, mineId);
    if (g.result === 'W') h2h.wins++;
    else if (g.result === 'L') h2h.losses++;
    else h2h.ties++;
    const isLater =
      !lastMeeting ||
      m.season > lastMeeting.season ||
      (m.season === lastMeeting.season && wk(m) > lastMeeting.week);
    if (isLater) lastMeeting = { ...g, season: m.season, week: wk(m) };
  }
  return { h2h, lastMeeting };
}

/**
 * Everything the My Team page shows for a claimed team (frontend/my-team), derived
 * client-side from the league's matchups with the same calculations the Matchups page,
 * playoff predictor, lineup-efficiency chip and weekly awards use.
 *
 * Returns null when the claimed owner has no team in the current season (the page then
 * shows the picker again).
 */
export function computeMyTeam(
  input: MyTeamInput,
  claimedOwnerId: string | null,
): MyTeamView | null {
  const {
    matchups,
    standings,
    migrationMapping,
    settings,
    season,
    draftPicks,
  } = input;
  const seasonMatchups = matchups.filter((m) => m.season === season);
  const teams = listSeasonTeams(seasonMatchups, season);
  const claimed = resolveClaimedTeam(teams, claimedOwnerId, migrationMapping);
  if (!claimed) return null;

  const records = seasonRecords(seasonMatchups, teams);
  const team = records.get(claimed.teamId)!;

  const unplayed = seasonMatchups.filter(isUnplayedMatchup);
  const playedWeeks = seasonMatchups
    .filter((m) => !isUnplayedMatchup(m))
    .map(wk);

  if (unplayed.length === 0) {
    const lastPlayed = playedWeeks.length ? Math.max(...playedWeeks) : null;
    const remap = (id: string) => migrationMapping.get(id) ?? id;
    const standing = standings.find(
      (s) =>
        s.season === season && remap(s.owner_id) === remap(claimed.ownerId),
    );
    return {
      kind: 'offseason',
      season,
      team,
      finalRank: standing?.final_rank ?? null,
      champion: standing?.champion === 'Yes',
      longestWinStreak: longestWinStreak(seasonMatchups, team.teamId),
      efficiency: computeEfficiency(seasonMatchups, team.teamId, lastPlayed),
      awards: computeAwards(seasonMatchups, team.teamId, lastPlayed),
      topDraftPicks: topDraftPicks(draftPicks, team.teamId),
    };
  }

  const myUnplayed = unplayed.filter((m) => involves(m, team.teamId));
  // League-wide: a week with no game for the claimed team (a bye) still counts.
  const currentWeek = Math.min(...unplayed.map(wk));
  const earlier = playedWeeks.filter((w) => w < currentWeek);
  const lastWeek = earlier.length ? Math.max(...earlier) : null;

  const lastGame =
    lastWeek == null
      ? undefined
      : seasonMatchups.find(
          (m) =>
            wk(m) === lastWeek &&
            involves(m, team.teamId) &&
            !isUnplayedMatchup(m),
        );

  // Odds change: the same model with last week's regular-season games reset to
  // unplayed (0–0), which also drops those scores from the scoring distributions.
  const playoffOdds = oddsFor(seasonMatchups, settings, team.teamId);
  let playoffOddsChange: number | null = null;
  const lastWeekIsRegular =
    lastWeek != null &&
    seasonMatchups.some((m) => wk(m) === lastWeek && isRegularSeason(m));
  if (lastWeekIsRegular) {
    const rolledBack = seasonMatchups.map((m) =>
      wk(m) === lastWeek && isRegularSeason(m)
        ? { ...m, team_a_score: 0, team_b_score: 0 }
        : m,
    );
    playoffOddsChange =
      playoffOdds - oddsFor(rolledBack, settings, team.teamId);
  }

  const thisWeekGame = myUnplayed.find((m) => wk(m) === currentWeek);
  let matchup: ThisWeekMatchup | null = null;
  if (thisWeekGame) {
    const oppId =
      thisWeekGame.team_a_id === team.teamId
        ? thisWeekGame.team_b_id
        : thisWeekGame.team_a_id;
    const opponent = records.get(oppId)!;
    const preview = buildMatchupPreview(seasonMatchups, team.teamId, oppId);
    const opponentLast3 = seasonMatchups
      .filter((m) => involves(m, oppId) && !isUnplayedMatchup(m))
      .sort((a, b) => wk(a) - wk(b))
      .slice(-3)
      .map((m) => scoreFor(m, oppId).result);
    matchup = {
      opponent,
      projMine: preview.projA,
      projOpp: preview.projB,
      winProbMine: preview.winProbA,
      winProbOpp: preview.winProbB,
      ...headToHead(matchups, migrationMapping, team.ownerId, opponent.ownerId),
      opponentLast3,
    };
  }

  return {
    kind: 'in-season',
    season,
    team,
    currentWeek,
    lastWeek,
    lastWeekGame: lastGame ? scoreFor(lastGame, team.teamId) : null,
    playoffOdds,
    playoffOddsChange,
    efficiency: computeEfficiency(seasonMatchups, team.teamId, lastWeek),
    matchup,
    awards: computeAwards(seasonMatchups, team.teamId, lastWeek),
    topDraftPicks: topDraftPicks(draftPicks, team.teamId),
  };
}
