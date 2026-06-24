import { ChevronDown, Gem, Info, X } from 'lucide-react';
import { Fragment, Suspense, use, useCallback, useMemo, useState } from 'react';

import { type DraftPickItem, getDraftData } from './api-calls';

import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { POSITION_COLORS, positionColorMeta } from '@/lib/color-constants';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';

// ── Local color overrides (brighter than shared UI_COLORS for this page) ──────

const GREEN = '#16a34a';
const RED = '#dc2626';
const GREEN_BG = '#dcfce7';
const RED_BG = '#fee2e2';

// ── Constants ─────────────────────────────────────────────────────────────────

// ── Types ─────────────────────────────────────────────────────────────────────

type DraftResult = Result<DraftPickItem[]>;

// ── Constants ─────────────────────────────────────────────────────────────────

const STEAL_DELTA_MIN = 5; // draft_rank_delta >= this → steal
const BUST_DELTA_MAX = -5; // draft_rank_delta <= this → potential bust
const BUST_ROUND_BUFFER = 4; // bust only when picked more than this many rounds before the last
const BUST_ROUND_MAX = 10; // only flag busts / show alternatives for rounds 1–10
const ALT_PICK_ROUND_WINDOW = 2; // suggest alternatives within this many rounds of the pick
const AUCTION_BUST_MIN_BID = 5; // auction: only flag busts on players that cost more than this

const DELTA_PILL_POS = 3;
const DELTA_PILL_NEG = -3;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getAlts(
  pick: DraftPickItem,
  allPicks: DraftPickItem[],
  isAuction: boolean,
): DraftPickItem[] {
  // A pick with no scoring row has no point total to compare against, so it can
  // neither be an alternative nor have alternatives suggested for it.
  if (pick.total_points == null) return [];
  return allPicks
    .filter((a) =>
      a.total_points == null
        ? false
        : isAuction
          ? a.position === pick.position &&
            a.player_name !== pick.player_name &&
            a.team_id !== pick.team_id &&
            a.bid_amount <= pick.bid_amount &&
            a.total_points > pick.total_points!
          : a.position === pick.position &&
            a.overall_pick_number > pick.overall_pick_number &&
            a.round <= pick.round + ALT_PICK_ROUND_WINDOW &&
            a.player_name !== pick.player_name &&
            a.team_id !== pick.team_id &&
            a.total_points > pick.total_points!,
    )
    .sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0))
    .slice(0, 2);
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DraftGradesSkeleton() {
  return (
    <div className="w-full max-w-250">
      <div className="flex items-center gap-2.5 mb-6">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-8 w-24 ml-2" />
        <Skeleton className="h-8 w-36" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-lg" />
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────

interface DraftGradesContentProps {
  promise: Promise<DraftResult>;
  seasons: string[];
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
  isDemo: boolean;
  demoAuction: boolean;
  onDemoAuctionChange: (auction: boolean) => void;
}

function DraftGradesContent({
  promise,
  seasons,
  selectedSeason,
  onSeasonChange,
  isDemo,
  demoAuction,
  onDemoAuctionChange,
}: DraftGradesContentProps) {
  const result = use(promise);

  const allPicks = useMemo(() => (result.ok ? result.data : []), [result]);

  // Auction vs. snake is driven entirely by the loaded dataset's flag. In demo
  // mode a Switch (below) chooses which dataset the parent fetches.
  const isAuction = allPicks[0]?.is_auction ?? false;
  const fmtBid = (n: number) => `$${n}`;
  const pickLabel = (pick: DraftPickItem) =>
    isAuction
      ? fmtBid(pick.bid_amount)
      : `Rd ${pick.round} · Pick ${pick.overall_pick_number}`;

  const managers = useMemo(() => {
    const seen = new Map<string, { id: string; username: string }>();
    for (const p of allPicks) {
      if (!seen.has(p.team_id)) {
        seen.set(p.team_id, { id: p.team_id, username: p.owner_username });
      }
    }
    return [...seen.values()].sort((a, b) =>
      a.username.localeCompare(b.username),
    );
  }, [allPicks]);

  const [rawSelectedManager, setSelectedManager] = useState(
    managers[0]?.id ?? '',
  );
  const [openBusts, setOpenBusts] = useState<Record<string, boolean>>({});

  // Derive the effective selection during render so a stale id (after the
  // manager list changes) falls back to the first manager without an effect.
  const selectedManager = managers.some((m) => m.id === rawSelectedManager)
    ? rawSelectedManager
    : (managers[0]?.id ?? '');

  const picks = useMemo(
    () => allPicks.filter((p) => p.team_id === selectedManager),
    [allPicks, selectedManager],
  );

  // Best/worst grading needs a draft_rank_delta; picks with null analytics
  // (e.g. D/ST, kickers, unscored players) are excluded per FE-013.
  const scorablePicks = picks.filter(
    (p) =>
      p.position !== 'K' && p.position !== 'D/ST' && p.draft_rank_delta != null,
  );

  const bestPick = scorablePicks.length
    ? scorablePicks.reduce((best, p) =>
        (p.draft_rank_delta ?? 0) > (best.draft_rank_delta ?? 0) ? p : best,
      )
    : null;

  const worstPick = scorablePicks.length
    ? scorablePicks.reduce((worst, p) =>
        (p.draft_rank_delta ?? 0) < (worst.draft_rank_delta ?? 0) ? p : worst,
      )
    : null;

  const maxRound = allPicks.length
    ? Math.max(...allPicks.map((p) => p.round))
    : 0;
  const isBustPick = useCallback(
    (p: DraftPickItem) =>
      p.draft_rank_delta != null &&
      p.draft_rank_delta <= BUST_DELTA_MAX &&
      (isAuction
        ? p.bid_amount > AUCTION_BUST_MIN_BID
        : p.round <= maxRound - BUST_ROUND_BUFFER && p.round <= BUST_ROUND_MAX),
    [isAuction, maxRound],
  );
  const busts = picks.filter(isBustPick).length;
  const steals = picks.filter(
    (p) => p.draft_rank_delta != null && p.draft_rank_delta >= STEAL_DELTA_MIN,
  ).length;

  const toggleBust = (key: string) => {
    setOpenBusts((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const bustsWithAlts = useMemo(
    () =>
      picks.flatMap((pick, i) => {
        if (!isBustPick(pick)) return [];
        const alts = getAlts(pick, allPicks, isAuction);
        if (alts.length === 0) return [];
        return [
          { pick, alts, bustKey: `${selectedManager}-${selectedSeason}-${i}` },
        ];
      }),
    [picks, allPicks, isAuction, isBustPick, selectedManager, selectedSeason],
  );

  const bustsWithAltsMap = useMemo(
    () => new Map(bustsWithAlts.map((item) => [item.bustKey, item])),
    [bustsWithAlts],
  );

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">
        {result.error}
      </p>
    );
  }

  return (
    <TooltipProvider>
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 mb-6">
        <div className="flex items-center gap-2.5">
          <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto">
            Season
          </span>
          <select
            className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
            value={selectedSeason}
            onChange={(e) => onSeasonChange(e.target.value)}
          >
            {[...seasons]
              .sort((a, b) => Number(b) - Number(a))
              .map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
          </select>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto sm:ml-2">
            Manager
          </span>
          <select
            className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
            value={selectedManager}
            onChange={(e) => setSelectedManager(e.target.value)}
          >
            {managers.map((mgr) => (
              <option key={mgr.id} value={mgr.id}>
                {mgr.username}
              </option>
            ))}
          </select>
        </div>
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

      {/* Stat Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Best pick
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  The player who most outperformed their drafted position rank —
                  the pick with the highest rank delta. K and D/ST are excluded.
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {bestPick ? bestPick.player_name : '—'}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {bestPick ? pickLabel(bestPick) : ''}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Worst pick
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  The player who most underperformed their drafted position rank
                  — the pick with the lowest rank delta. K and D/ST are
                  excluded.
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {worstPick ? worstPick.player_name : '—'}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {worstPick ? pickLabel(worstPick) : ''}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Steals
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  A steal is a player whose actual finish at their position was
                  5 or more spots better than where they were drafted.
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium" style={{ color: GREEN }}>
            {steals}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Busts
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  A bust is a player whose actual finish at their position was 5
                  or more spots worse than where they were drafted.{' '}
                  {isAuction
                    ? `Only players that cost more than ${fmtBid(AUCTION_BUST_MIN_BID)} are considered.`
                    : 'Only picks from rounds 1-10 are considered.'}
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium" style={{ color: RED }}>
            {busts}
          </div>
        </div>
      </div>

      {/* Picks Table */}
      <div className="bg-card border border-border/50 rounded-lg mb-6 max-h-[70vh] overflow-auto">
        <table className="w-full border-separate border-spacing-0 table-fixed text-[12px]">
          <thead className="sticky top-0 z-30">
            <tr>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50 sticky left-0 z-20"
                style={{ width: '28px' }}
              >
                #
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50 sticky left-7 z-20"
                style={{ width: '180px' }}
              >
                Player
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '56px' }}
              >
                Pos
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '80px' }}
              >
                Total pts
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '72px' }}
              >
                <span className="inline-flex items-center justify-center gap-1">
                  VORP
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3 h-3 cursor-default" />
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      Value Over Replacement Player: the points a player scored
                      above a replacement-level player at their position. For
                      example, in a 10-team league with one starting QB,
                      that&apos;s QB11.
                    </TooltipContent>
                  </Tooltip>
                </span>
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '100px' }}
              >
                Pos rank - draft
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '100px' }}
              >
                Pos rank - actual
              </th>
              <th
                className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50"
                style={{ width: '90px' }}
              >
                Rank delta
              </th>
            </tr>
          </thead>
          <tbody>
            {picks.map((pick, i) => {
              const pm = positionColorMeta(pick.position);
              const delta = pick.draft_rank_delta;
              const deltaStr =
                delta == null ? '—' : (delta >= 0 ? '+' : '') + delta;
              const dpillCls =
                delta == null
                  ? 'delta-neu'
                  : delta >= DELTA_PILL_POS
                    ? 'delta-pos'
                    : delta <= DELTA_PILL_NEG
                      ? 'delta-neg'
                      : 'delta-neu';
              const isBust = isBustPick(pick);
              const bustKey = `${selectedManager}-${selectedSeason}-${i}`;
              const bustData = bustsWithAltsMap.get(bustKey);
              const isOpen = !!openBusts[bustKey];

              return (
                <Fragment key={`${pick.pick_id}-${i}`}>
                  <tr>
                    <td className="border-b border-border/50 sticky left-0 z-10 bg-card">
                      <div className="px-3 py-2.5 text-muted-foreground text-[11px]">
                        {i + 1}
                      </div>
                    </td>
                    <td className="border-b border-border/50 sticky left-7 z-10 bg-card">
                      <div className="px-3 py-2.5">
                        <div className="text-[13px] font-medium text-foreground flex items-center gap-1">
                          {pick.player_name}
                          {pick.draft_rank_delta != null &&
                            pick.draft_rank_delta >= STEAL_DELTA_MIN && (
                              <Gem
                                className="w-3 h-3 shrink-0"
                                style={{ color: GREEN }}
                              />
                            )}
                          {isBust && (
                            <X
                              className="w-3 h-3 shrink-0"
                              style={{ color: RED }}
                            />
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground">
                            {pickLabel(pick)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 flex justify-center">
                        <span
                          className="inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                          style={{ background: pm.bg, color: pm.tc }}
                        >
                          {pick.position}
                        </span>
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 text-center text-[13px] font-medium text-foreground">
                        {pick.total_points != null
                          ? pick.total_points.toFixed(2)
                          : '—'}
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      {pick.vorp === null ? (
                        <div className="px-3 py-2.5 text-center text-[12px] text-muted-foreground">
                          N/A
                        </div>
                      ) : (
                        <div
                          className="px-3 py-2.5 text-center text-[13px] font-medium"
                          style={{ color: pick.vorp >= 0 ? GREEN : RED }}
                        >
                          {(pick.vorp >= 0 ? '+' : '') + pick.vorp.toFixed(1)}
                        </div>
                      )}
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 text-center text-[13px] font-medium text-foreground">
                        {pick.drafted_position_rank}
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 text-center text-[13px] font-medium text-foreground">
                        {pick.actual_position_rank ?? '—'}
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 flex justify-center">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${dpillCls}`}
                          style={{
                            background:
                              dpillCls === 'delta-pos'
                                ? GREEN_BG
                                : dpillCls === 'delta-neg'
                                  ? RED_BG
                                  : POSITION_COLORS.K.bg,
                            color:
                              dpillCls === 'delta-pos'
                                ? GREEN
                                : dpillCls === 'delta-neg'
                                  ? RED
                                  : POSITION_COLORS.K.tc,
                          }}
                        >
                          {delta == null ? deltaStr : `${deltaStr} places`}
                        </span>
                      </div>
                    </td>
                  </tr>
                  {bustData && (
                    <tr className="hidden sm:table-row">
                      <td colSpan={8} className="border-b border-border/50 p-0">
                        <div className="bg-muted/50 border-b border-border/50 px-3 py-2 flex items-center justify-between">
                          <span
                            className="text-[10px] font-medium uppercase tracking-[0.06em]"
                            style={{ color: RED }}
                          >
                            Could have picked instead
                          </span>
                          <button
                            className="bg-transparent border-none cursor-pointer text-[11px] text-muted-foreground p-0 flex items-center gap-1"
                            onClick={() => toggleBust(bustKey)}
                          >
                            {isOpen ? 'Hide' : 'Show'} alternatives
                            <ChevronDown
                              className="w-2.5 h-2.5 transition-transform"
                              style={{
                                transform: isOpen ? 'rotate(180deg)' : 'none',
                              }}
                            />
                          </button>
                        </div>
                        {isOpen && (
                          <div className="flex flex-col divide-y divide-border/50">
                            {bustData.alts.map((alt, altIdx) => {
                              const altPm = positionColorMeta(alt.position);
                              const diff = (
                                (alt.total_points ?? 0) -
                                (pick.total_points ?? 0)
                              ).toFixed(2);
                              const altLabel = isAuction
                                ? `${fmtBid(pick.bid_amount - alt.bid_amount)} cheaper`
                                : `Picked ${alt.overall_pick_number - pick.overall_pick_number} spots later`;
                              return (
                                <div
                                  key={`${alt.pick_id}-${altIdx}`}
                                  className="flex items-center gap-3 px-3 py-2.5 bg-muted/30"
                                >
                                  <span
                                    className="inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                                    style={{
                                      background: altPm.bg,
                                      color: altPm.tc,
                                    }}
                                  >
                                    {alt.position}
                                  </span>
                                  <span className="text-[12px] font-medium text-foreground flex-1">
                                    {alt.player_name}
                                  </span>
                                  <span className="text-[11px] text-muted-foreground">
                                    {altLabel}
                                  </span>
                                  <span className="text-[13px] font-medium text-foreground">
                                    {(alt.total_points ?? 0).toFixed(2)} pts
                                  </span>
                                  <span
                                    className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap"
                                    style={{
                                      background: GREEN_BG,
                                      color: GREEN,
                                    }}
                                  >
                                    +{diff} more points
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Bust Alternatives */}
      {bustsWithAlts.length > 0 && (
        <div className="flex flex-col gap-2.5 sm:hidden">
          {bustsWithAlts.map(({ pick, alts, bustKey }) => {
            const isOpen = !!openBusts[bustKey];
            return (
              <div
                key={bustKey}
                className="bg-card border border-border/50 rounded-lg overflow-hidden"
              >
                <div className="bg-muted/50 border-b border-border/50 p-2.5 flex items-center justify-between">
                  <div>
                    <div
                      className="text-[10px] font-medium uppercase tracking-[0.06em] mb-0.5"
                      style={{ color: RED }}
                    >
                      Could have picked instead
                    </div>
                    <div className="text-[12px] font-medium text-foreground flex items-center gap-1">
                      <X className="w-3 h-3 shrink-0" style={{ color: RED }} />
                      {pick.player_name}
                      <span className="text-[11px] text-muted-foreground font-normal ml-1">
                        {pickLabel(pick)}
                      </span>
                    </div>
                  </div>
                  <button
                    className="bg-transparent border-none cursor-pointer text-[11px] text-muted-foreground p-0 flex items-center gap-1 shrink-0 ml-4"
                    onClick={() => toggleBust(bustKey)}
                  >
                    {isOpen ? 'Hide' : 'Show'} alternatives
                    <ChevronDown
                      className="w-2.5 h-2.5 transition-transform"
                      style={{ transform: isOpen ? 'rotate(180deg)' : 'none' }}
                    />
                  </button>
                </div>
                {isOpen && (
                  <div className="p-2.5 flex flex-col gap-1.5">
                    {alts.map((alt, altIdx) => {
                      const altPm = positionColorMeta(alt.position);
                      const diff = (
                        (alt.total_points ?? 0) - (pick.total_points ?? 0)
                      ).toFixed(2);
                      const altLabel = isAuction
                        ? `${fmtBid(pick.bid_amount - alt.bid_amount)} cheaper`
                        : `Picked ${alt.overall_pick_number - pick.overall_pick_number} spots later`;
                      return (
                        <div
                          key={`${alt.pick_id}-${altIdx}`}
                          className="flex items-center gap-2 px-2 py-1.5 bg-muted/50 border border-border/50 rounded-md"
                        >
                          <span
                            className="inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                            style={{ background: altPm.bg, color: altPm.tc }}
                          >
                            {alt.position}
                          </span>
                          <span className="text-[12px] font-medium text-foreground flex-1">
                            {alt.player_name}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            {altLabel}
                          </span>
                          <span className="text-[12px] font-medium text-foreground ml-auto">
                            {(alt.total_points ?? 0).toFixed(2)} pts
                          </span>
                          <span
                            className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap"
                            style={{ background: GREEN_BG, color: GREEN }}
                          >
                            +{diff} more points
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </TooltipProvider>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DraftGrades() {
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
      <div className="max-w-250 mx-auto w-full">
        <Suspense fallback={<DraftGradesSkeleton />}>
          <DraftGradesContent
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
