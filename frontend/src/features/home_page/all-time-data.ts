import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import type { MatchupItem } from '@/features/matchups/api-calls';
import { isUnplayedMatchup } from '@/lib/matchups';

export interface AllTimeStandingsData {
  standings: ManagerStandingsItem[];
  matchups: MatchupItem[];
  migrationMapping: Map<string, string>;
}

export interface AllTimeRow {
  ownerId: string;
  username: string;
  teamName: string;
  teamLogo: string | null;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  pa: number;
  games: number;
}

export function buildAllTimeStandings(
  standings: ManagerStandingsItem[],
  matchups: MatchupItem[],
  migrationMapping: Map<string, string>,
  mode: 'regular' | 'playoff',
): AllTimeRow[] {
  const remapOwner = (id: string) => migrationMapping.get(id) ?? id;

  // Most recent team identity per owner, for display in the table
  const ownerMeta = new Map<string, ManagerStandingsItem>();
  for (const row of standings) {
    const id = remapOwner(row.owner_id);
    const existing = ownerMeta.get(id);
    if (!existing || row.season.localeCompare(existing.season) > 0) {
      ownerMeta.set(id, row);
    }
  }

  const acc = new Map<string, AllTimeRow>();
  const ensure = (
    ownerId: string,
    fallbackName: string,
    fallbackLogo: string | null,
  ) => {
    let row = acc.get(ownerId);
    if (!row) {
      const meta = ownerMeta.get(ownerId);
      row = {
        ownerId,
        username: meta?.owner_username ?? fallbackName,
        teamName: meta?.team_name ?? '',
        teamLogo: meta?.team_logo ?? fallbackLogo,
        wins: 0,
        losses: 0,
        ties: 0,
        pf: 0,
        pa: 0,
        games: 0,
      };
      acc.set(ownerId, row);
    }
    return row;
  };

  for (const m of matchups) {
    // Unplayed 0-0 placeholder weeks add no wins/losses/ties or PF/PA.
    if (isUnplayedMatchup(m)) continue;
    // Playoff standings only count winners' bracket games
    const include =
      mode === 'regular'
        ? m.playoff_tier_type === 'NONE'
        : m.playoff_tier_type === 'WINNERS_BRACKET';
    if (!include) continue;

    const aOwner = remapOwner(m.team_a_primary_owner_id);
    const bOwner = remapOwner(m.team_b_primary_owner_id);
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);

    const a = ensure(aOwner, m.team_a_display_name, m.team_a_team_logo);
    const b = ensure(bOwner, m.team_b_display_name, m.team_b_team_logo);

    a.games++;
    b.games++;
    a.pf += aScore;
    a.pa += bScore;
    b.pf += bScore;
    b.pa += aScore;
    if (aScore > bScore) {
      a.wins++;
      b.losses++;
    } else if (aScore < bScore) {
      a.losses++;
      b.wins++;
    } else {
      a.ties++;
      b.ties++;
    }
  }

  const winPct = (r: AllTimeRow) =>
    r.games > 0 ? (r.wins + 0.5 * r.ties) / r.games : 0;

  return [...acc.values()]
    .filter((r) => r.games > 0)
    .sort((a, b) => b.wins - a.wins || winPct(b) - winPct(a) || b.pf - a.pf);
}
