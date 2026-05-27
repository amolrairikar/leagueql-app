import React, { Suspense, use, useEffect, useMemo, useState } from 'react';
import { ChevronDown, Gem, Info, X } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { POSITION_COLORS } from '@/lib/color-constants';
import { type DraftPickItem, getDraftData } from './api-calls';

// ── Local color overrides (brighter than shared UI_COLORS for this page) ──────

const GREEN  = '#16a34a';
const RED    = '#dc2626';
const GREEN_BG = '#dcfce7';
const RED_BG   = '#fee2e2';

// ── Constants ─────────────────────────────────────────────────────────────────

const posMeta: Record<string, { bg: string; tc: string }> = {
  QB: { bg: POSITION_COLORS.QB.bg, tc: POSITION_COLORS.QB.tc },
  RB: { bg: POSITION_COLORS.RB.bg, tc: POSITION_COLORS.RB.tc },
  WR: { bg: POSITION_COLORS.WR.bg, tc: POSITION_COLORS.WR.tc },
  TE: { bg: POSITION_COLORS.TE.bg, tc: POSITION_COLORS.TE.tc },
  K: { bg: POSITION_COLORS.K.bg, tc: POSITION_COLORS.K.tc },
  'D/ST': { bg: POSITION_COLORS.DEF.bg, tc: POSITION_COLORS.DEF.tc },
};

// ── Types ─────────────────────────────────────────────────────────────────────

type DraftResult =
  | { ok: true; data: DraftPickItem[] }
  | { ok: false; error: string };

// ── Constants ─────────────────────────────────────────────────────────────────

const STEAL_DELTA_MIN       = 5;   // draft_rank_delta >= this → steal
const BUST_DELTA_MAX        = -10; // draft_rank_delta <= this → potential bust
const BUST_ROUND_BUFFER     = 4;   // bust only when picked more than this many rounds before the last
const BUST_ROUND_MAX        = 10;  // only flag busts / show alternatives for rounds 1–10
const ALT_PICK_ROUND_WINDOW = 2;   // suggest alternatives within this many rounds of the pick

const DELTA_PILL_POS = 3;
const DELTA_PILL_NEG = -3;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getAlts(pick: DraftPickItem, allPicks: DraftPickItem[]): DraftPickItem[] {
  return allPicks
    .filter(
      (a) =>
        a.position === pick.position &&
        a.overall_pick_number > pick.overall_pick_number &&
        a.round <= pick.round + ALT_PICK_ROUND_WINDOW &&
        a.player_name !== pick.player_name &&
        a.team_id !== pick.team_id &&
        a.total_points > pick.total_points,
    )
    .sort((a, b) => b.total_points - a.total_points)
    .slice(0, 2);
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DraftRecapSkeleton() {
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

  const managers = useMemo(() => {
    const seen = new Map<string, { id: string; username: string }>();
    for (const p of allPicks) {
      if (!seen.has(p.team_id)) {
        seen.set(p.team_id, { id: p.team_id, username: p.owner_username });
      }
    }
    return [...seen.values()].sort((a, b) => a.username.localeCompare(b.username));
  }, [allPicks]);

  const [selectedManager, setSelectedManager] = useState(managers[0]?.id ?? '');
  const [openBusts, setOpenBusts] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (managers.length > 0 && !managers.find((m) => m.id === selectedManager)) {
      setSelectedManager(managers[0].id);
    }
  }, [managers, selectedManager]);

  const picks = useMemo(
    () => allPicks.filter((p) => p.team_id === selectedManager),
    [allPicks, selectedManager],
  );

  const bestPick = picks.length
    ? picks.reduce((best, p) =>
        p.draft_rank_delta > best.draft_rank_delta ? p : best,
      )
    : null;

  const maxRound = allPicks.length ? Math.max(...allPicks.map((p) => p.round)) : 0;
  const busts = picks.filter((p) => p.draft_rank_delta <= BUST_DELTA_MAX && p.round <= maxRound - BUST_ROUND_BUFFER && p.round <= BUST_ROUND_MAX).length;
  const steals = picks.filter((p) => p.draft_rank_delta >= STEAL_DELTA_MIN).length;

  const totalVorp = picks.reduce((sum, p) => sum + (p.vorp ?? 0), 0);

  const toggleBust = (key: string) => {
    setOpenBusts((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">{result.error}</p>
    );
  }

  return (
    <TooltipProvider>
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 mb-6">
        <div className="flex items-center gap-2.5">
          <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto">Season</span>
          <select
            className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
            value={selectedSeason}
            onChange={(e) => onSeasonChange(e.target.value)}
          >
            {[...seasons].sort((a, b) => Number(b) - Number(a)).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto sm:ml-2">Manager</span>
          <select
            className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
            value={selectedManager}
            onChange={(e) => setSelectedManager(e.target.value)}
          >
            {managers.map((mgr) => (
              <option key={mgr.id} value={mgr.id}>{mgr.username}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Stat Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Total VORP
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  Value Over Replacement Player — how many more points this player scored compared to a league-average player at the same position. Not calculated for K and D/ST, as these positions are typically streamed.
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {picks.length ? totalVorp.toFixed(1) : '—'}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1">
              Best pick
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 cursor-default" />
                </TooltipTrigger>
                <TooltipContent side="top">
                  The player who most outperformed their drafted position rank — the pick with the highest rank delta.
                </TooltipContent>
              </Tooltip>
            </span>
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {bestPick ? bestPick.player_name : '—'}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {bestPick ? `Rd ${bestPick.round}, Pick ${bestPick.overall_pick_number}` : ''}
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
                  A steal is a player whose actual finish at their position was 5 or more spots better than where they were drafted.
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
                  A bust is a player whose actual finish at their position was 10 or more spots worse than where they were drafted. Only picks from rounds 1–10 are considered.
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
      <div className="bg-card border border-border/50 rounded-lg mb-6 overflow-x-auto">
        <table className="w-full border-separate border-spacing-0 table-fixed text-[12px]">
          <thead className="sticky top-0 z-10">
            <tr>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50 sticky left-0 z-20" style={{ width: '28px' }}>
                #
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50 sticky left-[28px] z-20" style={{ width: '180px' }}>
                Player
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '56px' }}>
                Pos
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '80px' }}>
                Total pts
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '72px' }}>
                VORP
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '100px' }}>
                Pos rank - draft
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '100px' }}>
                Pos rank - actual
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-center bg-muted border-b border-border/50" style={{ width: '90px' }}>
                Rank delta
              </th>
            </tr>
          </thead>
          <tbody>
            {picks.map((pick, i) => {
              const pm = posMeta[pick.position] ?? { bg: POSITION_COLORS.K.bg, tc: POSITION_COLORS.K.tc };
              const delta = pick.draft_rank_delta;
              const deltaStr = (delta >= 0 ? '+' : '') + delta;
              const dpillCls = delta >= DELTA_PILL_POS ? 'delta-pos' : delta <= DELTA_PILL_NEG ? 'delta-neg' : 'delta-neu';
              const isBust = delta <= BUST_DELTA_MAX && pick.round <= maxRound - BUST_ROUND_BUFFER && pick.round <= BUST_ROUND_MAX;
              const alts = isBust ? getAlts(pick, allPicks) : [];
              const bustKey = `${selectedManager}-${selectedSeason}-${i}`;
              const isOpen = !!openBusts[bustKey];

              return (
                <React.Fragment key={pick.pick_id}>
                  <tr>
                    <td className="border-b border-border/50 sticky left-0 z-10 bg-card">
                      <div className="px-3 py-2.5 text-muted-foreground text-[11px]">{i + 1}</div>
                    </td>
                    <td className="border-b border-border/50 sticky left-[28px] z-10 bg-card">
                      <div className="px-3 py-2.5">
                        <div className="text-[13px] font-medium text-foreground flex items-center gap-1">
                          {pick.player_name}
                          {pick.draft_rank_delta >= STEAL_DELTA_MIN && <Gem className="w-3 h-3 shrink-0" style={{ color: GREEN }} />}
                          {isBust && <X className="w-3 h-3 shrink-0" style={{ color: RED }} />}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground">
                            Rd {pick.round} · Pick {pick.overall_pick_number}
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
                        {pick.total_points.toFixed(2)}
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      {pick.vorp === null ? (
                        <div className="px-3 py-2.5 text-center text-[12px] text-muted-foreground">N/A</div>
                      ) : (
                        <div className="px-3 py-2.5 text-center text-[13px] font-medium" style={{ color: pick.vorp >= 0 ? GREEN : RED }}>
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
                        {pick.actual_position_rank}
                      </div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 flex justify-center">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${dpillCls}`}
                          style={{
                            background: dpillCls === 'delta-pos' ? GREEN_BG : dpillCls === 'delta-neg' ? RED_BG : POSITION_COLORS.K.bg,
                            color: dpillCls === 'delta-pos' ? GREEN : dpillCls === 'delta-neg' ? RED : POSITION_COLORS.K.tc,
                          }}
                        >
                          {deltaStr} places
                        </span>
                      </div>
                    </td>
                  </tr>
                  {alts.length > 0 && (
                    <tr>
                      <td colSpan={8} className="p-0">
                        <div className="bg-muted/50 border-t border-border/50 p-2.5 flex flex-col gap-1.5">
                          <div className="flex items-center justify-between mb-1">
                            <div className="text-[10px] font-medium uppercase tracking-[0.06em]" style={{ color: RED }}>
                              Could have picked instead
                            </div>
                            <button
                              className="bg-transparent border-none cursor-pointer text-[11px] text-muted-foreground p-0 flex items-center gap-1"
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
                            <div className="flex flex-col gap-1">
                              {alts.map((alt) => {
                                const altPm = posMeta[alt.position] ?? { bg: POSITION_COLORS.K.bg, tc: POSITION_COLORS.K.tc };
                                const diff = (alt.total_points - pick.total_points).toFixed(2);
                                const spotsLater = alt.overall_pick_number - pick.overall_pick_number;
                                return (
                                  <div
                                    key={alt.pick_id}
                                    className="flex items-center gap-2 px-2 py-1.5 bg-card border border-border/50 rounded-md"
                                  >
                                    <span
                                      className="inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                                      style={{ background: altPm.bg, color: altPm.tc }}
                                    >
                                      {alt.position}
                                    </span>
                                    <span className="text-[12px] font-medium text-foreground flex-1">{alt.player_name}</span>
                                    <span className="text-[11px] text-muted-foreground">Picked {spotsLater} spots later</span>
                                    <span className="text-[12px] font-medium text-foreground ml-auto">{alt.total_points.toFixed(2)} pts</span>
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
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </TooltipProvider>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DraftRecap() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason = [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);

  const draftPromise = useMemo(
    (): Promise<DraftResult> =>
      leagueId && selectedSeason
        ? getDraftData(leagueId, platform, selectedSeason)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err: unknown) => ({
              ok: false as const,
              error: err instanceof Error ? err.message : 'Failed to load draft data.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-250 mx-auto w-full">
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
