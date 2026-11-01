import {
  type ManagerStandingsItem,
  type MatchupItem,
} from '@/features/manager_history/api-calls';
import { managerInitials } from '@/features/manager_history/format';
import {
  type ManagerData,
  type RawBoxScoreSide,
  type RawScheduleGame,
  type RivalryAcc,
  type RivalryEntry,
  type ScheduleGame,
  type SeasonEntry,
} from '@/features/manager_history/types';
import { assignAvatarColors, avatarColor } from '@/lib/color-constants';
import { isUnplayedMatchup } from '@/lib/matchups';

export const DOMINATION_WIN_RATE = 0.65; // win rate at or above this → domination rivalry

export const NEMESIS_WIN_RATE = 0.4; // win rate below this → nemesis rivalry

// ── Helpers ───────────────────────────────────────────────────────────────────

export function processData(
  standings: ManagerStandingsItem[],
  matchups: MatchupItem[],
  migrationMapping: Map<string, string>,
): ManagerData[] {
  const ownerStandingsMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    const mappedId = migrationMapping.get(row.owner_id) ?? row.owner_id;
    if (!ownerStandingsMap.has(mappedId)) ownerStandingsMap.set(mappedId, []);
    ownerStandingsMap.get(mappedId)!.push(row);
  }

  const remapOwner = (ownerId: string) =>
    migrationMapping.get(ownerId) ?? ownerId;

  const highScoreMap = new Map<string, Map<string, number>>();
  const playoffMap = new Map<string, Set<string>>();
  const runnerUpMap = new Map<string, Set<string>>();

  const rivalryMap = new Map<string, Map<string, RivalryAcc>>();

  // Per-owner per-season schedule of every game played
  const scheduleMap = new Map<string, Map<string, RawScheduleGame[]>>();

  for (const m of matchups) {
    // Unplayed 0-0 placeholder weeks add no result, high score, or rivalry game.
    if (isUnplayedMatchup(m)) continue;
    const aOwner = remapOwner(m.team_a_primary_owner_id);
    const bOwner = remapOwner(m.team_b_primary_owner_id);
    const { season } = m;
    const week = parseInt(m.week, 10);
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);
    // Postseason includes winners, losers, and consolation brackets
    const isPostseason = m.playoff_tier_type !== 'NONE';

    const sideA: RawBoxScoreSide = {
      ownerId: aOwner,
      teamLogo: m.team_a_team_logo,
      teamName: m.team_a_team_name,
      ownerUsername: m.team_a_display_name,
      score: aScore,
      starters: m.team_a_starters,
      bench: m.team_a_bench,
      isWinner: aScore > bScore,
    };
    const sideB: RawBoxScoreSide = {
      ownerId: bOwner,
      teamLogo: m.team_b_team_logo,
      teamName: m.team_b_team_name,
      ownerUsername: m.team_b_display_name,
      score: bScore,
      starters: m.team_b_starters,
      bench: m.team_b_bench,
      isWinner: bScore > aScore,
    };

    // Build schedule entries from each team's perspective
    for (const [owner, own, opp] of [
      [aOwner, sideA, sideB],
      [bOwner, sideB, sideA],
    ] as [string, RawBoxScoreSide, RawBoxScoreSide][]) {
      if (!scheduleMap.has(owner)) scheduleMap.set(owner, new Map());
      const seasonMap = scheduleMap.get(owner)!;
      if (!seasonMap.has(season)) seasonMap.set(season, []);
      let result: 'W' | 'L' | 'T';
      if (own.score > opp.score) result = 'W';
      else if (own.score < opp.score) result = 'L';
      else result = 'T';
      seasonMap.get(season)!.push({ week, result, isPostseason, own, opp });
    }

    // High scores per owner per season
    for (const [owner, score] of [
      [aOwner, aScore],
      [bOwner, bScore],
    ] as [string, number][]) {
      if (!highScoreMap.has(owner)) highScoreMap.set(owner, new Map());
      const prev = highScoreMap.get(owner)!.get(season) ?? 0;
      if (score > prev) highScoreMap.get(owner)!.set(season, score);
    }

    // Playoff appearances and runner-up detection
    if (m.playoff_tier_type === 'WINNERS_BRACKET') {
      for (const owner of [aOwner, bOwner]) {
        if (!playoffMap.has(owner)) playoffMap.set(owner, new Set());
        playoffMap.get(owner)!.add(season);
      }
      if (m.playoff_round === 'Finals' && m.loser !== 'TIE' && m.loser !== '') {
        const loserOwner = m.loser === m.team_a_id ? aOwner : bOwner;
        if (!runnerUpMap.has(season)) runnerUpMap.set(season, new Set());
        runnerUpMap.get(season)!.add(loserOwner);
      }
    }

    // Head-to-head rivalry data across all matchups
    for (const [owner, opp, ownerScore, oppScore] of [
      [aOwner, bOwner, aScore, bScore],
      [bOwner, aOwner, bScore, aScore],
    ] as [string, string, number, number][]) {
      if (!rivalryMap.has(owner)) rivalryMap.set(owner, new Map());
      const oppMap = rivalryMap.get(owner)!;
      if (!oppMap.has(opp)) {
        oppMap.set(opp, {
          w: 0,
          l: 0,
          totalFor: 0,
          totalAgainst: 0,
          count: 0,
          lastSeason: '',
          lastWeek: 0,
          lastWon: false,
        });
      }
      const r = oppMap.get(opp)!;
      r.count++;
      r.totalFor += ownerScore;
      r.totalAgainst += oppScore;
      if (ownerScore > oppScore) r.w++;
      else if (ownerScore < oppScore) r.l++;
      if (
        season > r.lastSeason ||
        (season === r.lastSeason && week > r.lastWeek)
      ) {
        r.lastSeason = season;
        r.lastWeek = week;
        r.lastWon = ownerScore > oppScore;
      }
    }
  }

  // Sort owners alphabetically to get consistent color assignment
  const owners = [...ownerStandingsMap.entries()]
    .map(([ownerId, rows]) => {
      const mostRecent = [...rows].sort((a, b) =>
        b.season.localeCompare(a.season),
      )[0];
      return { ownerId, username: mostRecent.owner_username };
    })
    .sort((a, b) => a.username.localeCompare(b.username));

  const colorMap = assignAvatarColors(owners.map((o) => o.ownerId));

  const ownerUsernames = new Map<string, string>();
  const ownerCurrentTeams = new Map<string, string>();
  for (const [ownerId, rows] of ownerStandingsMap) {
    const mostRecent = [...rows].sort((a, b) =>
      b.season.localeCompare(a.season),
    )[0];
    ownerUsernames.set(ownerId, mostRecent.owner_username);
    ownerCurrentTeams.set(ownerId, mostRecent.team_name);
  }

  return owners.map(({ ownerId }, colorIdx) => {
    const rows = ownerStandingsMap.get(ownerId)!;
    const mostRecent = [...rows].sort((a, b) =>
      b.season.localeCompare(a.season),
    )[0];

    const allWins = rows.reduce((s, r) => s + r.wins, 0);
    const allLosses = rows.reduce((s, r) => s + r.losses, 0);
    const championships = rows.filter((r) => r.champion === 'Yes').length;
    const playoffs = playoffMap.get(ownerId)?.size ?? 0;

    const ownerHighs = highScoreMap.get(ownerId);
    const allTimeHigh =
      ownerHighs && ownerHighs.size > 0 ? Math.max(...ownerHighs.values()) : 0;

    const totalPf = rows.reduce((s, r) => s + r.total_pf, 0);
    const totalGames = rows.reduce((s, r) => s + r.games_played, 0);
    const avgPts = totalGames > 0 ? totalPf / totalGames : 0;

    const seasons: SeasonEntry[] = rows
      .map((r) => {
        const isChampion = r.champion === 'Yes';
        const isRunnerUp = runnerUpMap.get(r.season)?.has(ownerId) ?? false;
        const madePlayoffs = playoffMap.get(ownerId)?.has(r.season) ?? false;

        let result: SeasonEntry['result'];
        if (r.in_progress) result = null;
        else if (isChampion) result = 'champion';
        else if (isRunnerUp) result = 'runner';
        else if (madePlayoffs) result = 'playoff';
        else result = 'elim';

        let finish: number | null = r.final_rank ?? null;
        if (finish === null) {
          if (isChampion) finish = 1;
          else if (isRunnerUp) finish = 2;
        }

        const schedule: ScheduleGame[] = [
          ...(scheduleMap.get(ownerId)?.get(r.season) ?? []),
        ]
          .sort((a, b) => a.week - b.week)
          .map((g) => ({
            week: g.week,
            result: g.result,
            isPostseason: g.isPostseason,
            own: {
              ...g.own,
              color: colorMap.get(g.own.ownerId) ?? avatarColor(0),
            },
            opp: {
              ...g.opp,
              color: colorMap.get(g.opp.ownerId) ?? avatarColor(0),
            },
          }));

        return {
          year: r.season,
          team: r.team_name,
          record: r.record,
          pts: r.total_pf,
          avg: r.avg_pf,
          high: highScoreMap.get(ownerId)?.get(r.season) ?? 0,
          result,
          finish,
          schedule,
        };
      })
      .sort((a, b) => a.year.localeCompare(b.year));

    const rivalries: RivalryEntry[] = [
      ...(rivalryMap.get(ownerId) ?? new Map<string, RivalryAcc>()).entries(),
    ]
      .filter(([oppId]) => ownerUsernames.has(oppId))
      .map(([oppId, data]) => ({
        oppId,
        oppName: ownerUsernames.get(oppId)!,
        oppTeam: ownerCurrentTeams.get(oppId) ?? '',
        oppColor: colorMap.get(oppId) ?? avatarColor(0),
        oppInit: managerInitials(ownerUsernames.get(oppId)!),
        w: data.w,
        l: data.l,
        avgFor: data.count > 0 ? data.totalFor / data.count : 0,
        avgAgainst: data.count > 0 ? data.totalAgainst / data.count : 0,
        lastResult: data.lastWon ? ('W' as const) : ('L' as const),
      }));

    return {
      owner_id: ownerId,
      owner_username: mostRecent.owner_username,
      init: managerInitials(mostRecent.owner_username),
      color: colorMap.get(ownerId) ?? avatarColor(colorIdx),
      currentTeam: mostRecent.team_name,
      allTime: {
        wins: allWins,
        losses: allLosses,
        championships,
        playoffs,
        highScore: Math.round(allTimeHigh * 100) / 100,
        avgPts: Math.round(avgPts * 100) / 100,
      },
      seasons,
      rivalries,
    };
  });
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
