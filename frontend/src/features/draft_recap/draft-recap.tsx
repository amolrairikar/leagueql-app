import { type ReactNode, Suspense, use, useMemo, useState } from 'react';

import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import {
  type DraftPickItem,
  getDraftData,
} from '@/features/draft_grades/api-calls';
import SeasonSelect from '@/features/season_select/season-select';
import { avatarColor } from '@/lib/color-constants';
import { POSITION_COLORS } from '@/lib/color-constants';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
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

interface AuctionTeam extends BoardTeam {
  totalSpent: number;
  picks: DraftPickItem[];
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

// ── Pick cell ─────────────────────────────────────────────────────────────────

// A single drafted player, colored by position. `topRight` is the slot-specific
// badge — the overall pick number on the snake board, the winning bid on the
// auction spend board.
function PickCell({
  pick,
  topRight,
}: {
  pick: DraftPickItem;
  topRight: ReactNode;
}) {
  const pm = posStyle(pick.position);
  return (
    <div
      className="flex flex-col h-[4.5rem] rounded-md px-2 py-1.5"
      style={{ background: pm.bg, color: pm.tc }}
    >
      <div className="flex items-center justify-between gap-1 mb-0.5">
        <span className="text-[9px] font-semibold uppercase tracking-[0.04em]">
          {pick.position}
          {pick.keeper && ' · K'}
        </span>
        {topRight}
      </div>
      <span className="block text-[12px] font-medium leading-tight line-clamp-2 break-words">
        {pick.player_name}
      </span>
      <div className="mt-auto flex items-center justify-between gap-1 text-[10px] font-semibold opacity-80">
        <span>
          {pick.total_points != null
            ? `${pick.total_points.toFixed(1)} pts`
            : '—'}
        </span>
        <span>
          {pick.position}
          {pick.actual_position_rank ?? ''}
        </span>
      </div>
    </div>
  );
}

// ── Spend board (auction) ─────────────────────────────────────────────────────

// One column per team — auctions have no draft slots, so columns are ordered by
// total spend and each lists that team's roster from priciest pick down.
function SpendBoard({ teams }: { teams: AuctionTeam[] }) {
  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-auto max-h-[78vh]">
      <div className="flex">
        {teams.map((team, i) => (
          <div
            key={team.id}
            className="w-44 shrink-0 border-r border-border/50 last:border-r-0"
          >
            <div className="sticky top-0 z-10 bg-muted border-b border-border/50 px-2.5 py-2.5">
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
                  <span className="text-[11px] font-semibold text-muted-foreground">
                    ${team.totalSpent} spent
                  </span>
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-1.5 p-1.5">
              {team.picks.map((pick) => (
                <PickCell
                  key={pick.player_id}
                  pick={pick}
                  topRight={
                    <span className="text-[11px] font-bold">
                      ${pick.bid_amount}
                    </span>
                  }
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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
  isDemo: boolean;
  demoAuction: boolean;
  onDemoAuctionChange: (auction: boolean) => void;
}

function DraftRecapContent({
  promise,
  seasons,
  selectedSeason,
  onSeasonChange,
  isDemo,
  demoAuction,
  onDemoAuctionChange,
}: DraftRecapContentProps) {
  const result = use(promise);

  const allPicks = useMemo(() => (result.ok ? result.data : []), [result]);

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

  const isAuction = allPicks.some((p) => p.is_auction);

  // Auction columns: one per team, ordered by total spend, each team's picks
  // sorted priciest-first. A season is wholly auction or wholly snake.
  const auctionTeams = useMemo<AuctionTeam[]>(() => {
    const map = new Map<string, AuctionTeam>();
    for (const p of allPicks) {
      let team = map.get(p.team_id);
      if (!team) {
        team = {
          id: p.team_id,
          username: p.owner_username,
          teamName: p.team_name,
          logo: p.team_logo,
          firstPick: p.overall_pick_number,
          totalSpent: 0,
          picks: [],
        };
        map.set(p.team_id, team);
      }
      team.picks.push(p);
      team.totalSpent += p.bid_amount ?? 0;
    }
    const teams = [...map.values()];
    for (const team of teams) {
      team.picks.sort((a, b) => (b.bid_amount ?? 0) - (a.bid_amount ?? 0));
    }
    return teams.sort((a, b) => b.totalSpent - a.totalSpent);
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
        {isDemo && (
          <label className="flex items-center gap-2 cursor-pointer sm:ml-2">
            <span
              className={`text-[12px] font-medium ${demoAuction ? 'text-muted-foreground' : 'text-foreground'}`}
            >
              Snake
            </span>
            <Switch
              checked={demoAuction}
              onCheckedChange={onDemoAuctionChange}
              aria-label="Toggle auction draft display"
            />
            <span
              className={`text-[12px] font-medium ${demoAuction ? 'text-foreground' : 'text-muted-foreground'}`}
            >
              Auction
            </span>
          </label>
        )}
      </div>

      {teams.length === 0 ? (
        <p className="text-[13px] text-muted-foreground text-center py-8">
          No draft data available for this season.
        </p>
      ) : isAuction ? (
        <SpendBoard teams={auctionTeams} />
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
                    return (
                      <td
                        key={team.id}
                        className="w-40 border-b border-border/50 px-1.5 py-1.5 align-top"
                      >
                        <PickCell
                          pick={pick}
                          topRight={
                            <span className="text-[9px] font-medium opacity-70">
                              #{pick.overall_pick_number}
                            </span>
                          }
                        />
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
  const isDemo = useMemo(() => isDemoMode(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  // Demo-only toggle: selects the separate DRAFT_AUCTION dataset.
  const [demoAuction, setDemoAuction] = useState(false);

  const draftPromise = useMemo(
    (): Promise<DraftResult> =>
      leagueId && selectedSeason
        ? toResult(
            getDraftData(
              leagueId,
              platform,
              selectedSeason,
              isDemo && demoAuction,
            ).then((res) => res.data),
            'Failed to load draft data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason, isDemo, demoAuction],
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
            isDemo={isDemo}
            demoAuction={demoAuction}
            onDemoAuctionChange={setDemoAuction}
          />
        </Suspense>
      </div>
    </div>
  );
}
