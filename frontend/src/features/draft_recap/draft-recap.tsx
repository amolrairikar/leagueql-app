import { Suspense, use, useMemo, useState } from 'react';

import { avatarColor, TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  type DraftPickItem,
  getDraftData,
} from '@/features/draft_grades/api-calls';
import SeasonSelect from '@/features/season_select/season-select';
import { POSITION_COLORS } from '@/lib/color-constants';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';

// ── Types ─────────────────────────────────────────────────────────────────────

type DraftResult = Result<DraftPickItem[]>;

interface BoardTeam {
  id: string;
  username: string;
  teamName: string;
  logo: string;
  firstPick: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const posMeta: Record<string, { bg: string; tc: string }> = {
  QB: { bg: POSITION_COLORS.QB.bg, tc: POSITION_COLORS.QB.tc },
  RB: { bg: POSITION_COLORS.RB.bg, tc: POSITION_COLORS.RB.tc },
  WR: { bg: POSITION_COLORS.WR.bg, tc: POSITION_COLORS.WR.tc },
  TE: { bg: POSITION_COLORS.TE.bg, tc: POSITION_COLORS.TE.tc },
  K: { bg: POSITION_COLORS.K.bg, tc: POSITION_COLORS.K.tc },
  'D/ST': { bg: POSITION_COLORS.DEF.bg, tc: POSITION_COLORS.DEF.tc },
};

const posStyle = (position: string) =>
  posMeta[position] ?? { bg: POSITION_COLORS.K.bg, tc: POSITION_COLORS.K.tc };

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DraftRecapSkeleton() {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2.5 mb-6">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-8 w-28" />
      </div>
      <Skeleton className="h-[60vh] rounded-lg" />
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────

interface DraftRecapContentProps {
  promise: Promise<DraftResult>;
  seasons: string[];
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
}

function DraftRecapContent({
  promise,
  seasons,
  selectedSeason,
  onSeasonChange,
}: DraftRecapContentProps) {
  const result = use(promise);

  const allPicks = result.ok ? result.data : [];

  // Teams ordered by their draft slot. The team that made the earliest overall
  // pick owns the left-most column; in a snake draft the same team holds that
  // column every round even though the pick order reverses each round.
  const teams = useMemo<BoardTeam[]>(() => {
    const map = new Map<string, BoardTeam>();
    for (const p of allPicks) {
      const existing = map.get(p.team_id);
      if (!existing || p.overall_pick_number < existing.firstPick) {
        map.set(p.team_id, {
          id: p.team_id,
          username: p.owner_username,
          teamName: p.team_name,
          logo: p.team_logo,
          firstPick: p.overall_pick_number,
        });
      }
    }
    return [...map.values()].sort((a, b) => a.firstPick - b.firstPick);
  }, [allPicks]);

  // Look up a pick by its team + round so each board cell is O(1).
  const pickByTeamRound = useMemo(() => {
    const map = new Map<string, DraftPickItem>();
    for (const p of allPicks) map.set(`${p.team_id}-${p.round}`, p);
    return map;
  }, [allPicks]);

  const rounds = useMemo(() => {
    const maxRound = allPicks.length
      ? Math.max(...allPicks.map((p) => p.round))
      : 0;
    return Array.from({ length: maxRound }, (_, i) => i + 1);
  }, [allPicks]);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">
        {result.error}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2.5">
        <span className="text-[12px] font-medium text-muted-foreground">
          Season
        </span>
        <SeasonSelect
          seasons={seasons}
          value={selectedSeason}
          onValueChange={onSeasonChange}
        />
      </div>

      {teams.length === 0 ? (
        <p className="text-[13px] text-muted-foreground text-center py-8">
          No draft data available for this season.
        </p>
      ) : (
        <div className="bg-card border border-border/50 rounded-lg overflow-auto max-h-[78vh]">
          <table
            className="table-fixed border-separate border-spacing-0 text-[12px]"
            style={{ width: `${40 + teams.length * 160}px` }}
          >
            <thead className="sticky top-0 z-30">
              <tr>
                <th
                  className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-2 py-2.5 bg-muted border-b border-r border-border/50 sticky left-0 z-40"
                  style={{ width: '40px' }}
                >
                  Rd
                </th>
                {teams.map((team, i) => (
                  <th
                    key={team.id}
                    className="w-40 px-2.5 py-2.5 text-left align-bottom bg-muted border-b border-border/50"
                  >
                    <div className="flex items-center gap-2">
                      <TeamAvatar
                        teamLogo={team.logo}
                        teamName={team.teamName}
                        ownerUsername={team.username}
                        color={avatarColor(i)}
                      />
                      <div className="flex flex-col min-w-0">
                        <span className="text-[12px] font-medium text-foreground truncate">
                          {team.username}
                        </span>
                        <span
                          className="text-[11px] font-normal text-muted-foreground truncate"
                          title={team.teamName || `Team ${team.username}`}
                        >
                          {team.teamName || `Team ${team.username}`}
                        </span>
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rounds.map((round) => (
                <tr key={round}>
                  <td
                    className="text-center text-[11px] font-medium text-muted-foreground bg-card border-b border-r border-border/50 sticky left-0 z-20"
                    style={{ width: '40px' }}
                  >
                    {round}
                  </td>
                  {teams.map((team) => {
                    const pick = pickByTeamRound.get(`${team.id}-${round}`);
                    if (!pick) {
                      return (
                        <td
                          key={team.id}
                          className="w-40 border-b border-border/50"
                        />
                      );
                    }
                    const pm = posStyle(pick.position);
                    return (
                      <td
                        key={team.id}
                        className="w-40 border-b border-border/50 px-1.5 py-1.5 align-top"
                      >
                        <div
                          className="flex flex-col h-[4.5rem] rounded-md px-2 py-1.5"
                          style={{ background: pm.bg }}
                        >
                          <div className="flex items-center justify-between gap-1 mb-0.5">
                            <span
                              className="text-[9px] font-semibold uppercase tracking-[0.04em]"
                              style={{ color: pm.tc }}
                            >
                              {pick.position}
                              {pick.keeper && ' · K'}
                            </span>
                            <span
                              className="text-[9px] font-medium opacity-70"
                              style={{ color: pm.tc }}
                            >
                              #{pick.overall_pick_number}
                            </span>
                          </div>
                          <span
                            className="block text-[12px] font-medium leading-tight line-clamp-2 break-words"
                            style={{ color: pm.tc }}
                          >
                            {pick.player_name}
                          </span>
                          <div
                            className="mt-auto flex items-center justify-between gap-1 text-[10px] font-semibold opacity-80"
                            style={{ color: pm.tc }}
                          >
                            <span>{pick.total_points.toFixed(1)} pts</span>
                            <span>
                              {pick.position}
                              {pick.actual_position_rank}
                            </span>
                          </div>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DraftRecap() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);

  const draftPromise = useMemo(
    (): Promise<DraftResult> =>
      leagueId && selectedSeason
        ? toResult(
            getDraftData(leagueId, platform, selectedSeason).then(
              (res) => res.data,
            ),
            'Failed to load draft data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-[1400px] mx-auto w-full">
        <Suspense fallback={<DraftRecapSkeleton />}>
          <DraftRecapContent
            promise={draftPromise}
            seasons={seasons}
            selectedSeason={selectedSeason}
            onSeasonChange={setSelectedSeason}
          />
        </Suspense>
      </div>
    </div>
  );
}
