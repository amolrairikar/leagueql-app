import {
  type ChampionStandingsItem,
  type MatchupItem,
} from '@/features/manager_comparison/api-calls';
import {
  type GameLog,
  type Manager,
} from '@/features/manager_comparison/types';
import { avatarColor } from '@/lib/color-constants';
import { isUnplayedMatchup } from '@/lib/matchups';
import { initials } from '@/lib/utils';

export function longestWinStreak(
  games: GameLog[],
  side: 'left' | 'right',
): number {
  let best = 0;
  let current = 0;
  for (const g of games) {
    const won = side === 'left' ? g.lp > g.rp : g.rp > g.lp;
    if (won) {
      current++;
      if (current > best) best = current;
    } else {
      current = 0;
    }
  }
  return best;
}

export function buildManagers(
  matchups: MatchupItem[],
  standings: ChampionStandingsItem[],
  migrationMapping: Map<string, string>,
): Manager[] {
  const ownerMap = new Map<
    string,
    {
      name: string;
      team: string;
      scores: number[];
      wins: number;
      losses: number;
      ties: number;
    }
  >();
  // Distinct seasons each owner reached the winners bracket
  const playoffSeasons = new Map<string, Set<string>>();
  // Titles per owner, from the seasons whose STANDINGS row is flagged champion
  const championships = new Map<string, number>();
  for (const row of standings) {
    if (row.champion !== 'Yes') continue;
    const owner = migrationMapping.get(row.owner_id) ?? row.owner_id;
    championships.set(owner, (championships.get(owner) ?? 0) + 1);
  }

  for (const m of matchups) {
    // Unplayed 0-0 placeholder weeks contribute no record, scores, or playoff data.
    if (isUnplayedMatchup(m)) continue;
    for (const side of ['a', 'b'] as const) {
      const rawOwnerId = m[`team_${side}_primary_owner_id`];
      const ownerId = migrationMapping.get(rawOwnerId) ?? rawOwnerId;
      const displayName = m[`team_${side}_display_name`];
      const teamName = m[`team_${side}_team_name`];
      const score = Number(m[`team_${side}_score`]);

      if (!ownerMap.has(ownerId)) {
        ownerMap.set(ownerId, {
          name: displayName,
          team: teamName,
          scores: [],
          wins: 0,
          losses: 0,
          ties: 0,
        });
      }

      const entry = ownerMap.get(ownerId)!;
      entry.team = teamName;
      entry.scores.push(score);

      const otherSide = side === 'a' ? 'b' : 'a';
      const otherScore = Number(m[`team_${otherSide}_score`]);
      if (score > otherScore) entry.wins++;
      else if (score < otherScore) entry.losses++;
      else entry.ties++;
    }

    // Playoff appearances from the winners bracket
    if (m.playoff_tier_type === 'WINNERS_BRACKET') {
      const aOwner =
        migrationMapping.get(m.team_a_primary_owner_id) ??
        m.team_a_primary_owner_id;
      const bOwner =
        migrationMapping.get(m.team_b_primary_owner_id) ??
        m.team_b_primary_owner_id;
      for (const owner of [aOwner, bOwner]) {
        if (!playoffSeasons.has(owner)) playoffSeasons.set(owner, new Set());
        playoffSeasons.get(owner)!.add(m.season);
      }
    }
  }

  const sortedIds = [...ownerMap.keys()].sort((a, b) =>
    ownerMap.get(a)!.name.localeCompare(ownerMap.get(b)!.name),
  );

  return sortedIds.map((ownerId, i) => {
    const entry = ownerMap.get(ownerId)!;
    const scores = entry.scores;
    const avgPf =
      scores.length > 0 ? scores.reduce((s, x) => s + x, 0) / scores.length : 0;
    const highScore = scores.length > 0 ? Math.max(...scores) : 0;
    return {
      ownerId,
      name: entry.name,
      team: entry.team,
      color: avatarColor(i),
      init: initials(entry.name),
      stats: {
        wins: entry.wins,
        losses: entry.losses,
        ties: entry.ties,
        winPct:
          entry.wins + entry.losses + entry.ties > 0
            ? entry.wins / (entry.wins + entry.losses + entry.ties)
            : 0,
        avgPf,
        highScore,
        h2hWins: 0,
        longestStreak: 0,
        playoffApps: playoffSeasons.get(ownerId)?.size ?? 0,
        championships: championships.get(ownerId) ?? 0,
      },
    };
  });
}

export function buildGameLogs(
  matchups: MatchupItem[],
  leftOwnerId: string,
  rightOwnerId: string,
  migrationMapping: Map<string, string>,
): GameLog[] {
  const logs: GameLog[] = [];
  for (const m of matchups) {
    // Unplayed 0-0 placeholder weeks never appear in the head-to-head game log.
    if (isUnplayedMatchup(m)) continue;
    const aOwner =
      migrationMapping.get(m.team_a_primary_owner_id) ??
      m.team_a_primary_owner_id;
    const bOwner =
      migrationMapping.get(m.team_b_primary_owner_id) ??
      m.team_b_primary_owner_id;

    if (
      (aOwner === leftOwnerId && bOwner === rightOwnerId) ||
      (aOwner === rightOwnerId && bOwner === leftOwnerId)
    ) {
      const leftIsA = aOwner === leftOwnerId;
      logs.push({
        week: `Week ${m.week}`,
        season: m.season,
        lp: leftIsA ? Number(m.team_a_score) : Number(m.team_b_score),
        rp: leftIsA ? Number(m.team_b_score) : Number(m.team_a_score),
        matchupItem: m,
        leftIsA,
      });
    }
  }
  logs.sort((a, b) => {
    const seasonDiff = Number(a.season) - Number(b.season);
    if (seasonDiff !== 0) return seasonDiff;
    return (
      parseInt(a.week.replace('Week ', ''), 10) -
      parseInt(b.week.replace('Week ', ''), 10)
    );
  });
  return logs;
}
