import React, { Suspense, use, useEffect, useMemo, useState } from 'react';
import { ChevronDown, Gem, X } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';
import { TooltipProvider } from '@/components/ui/tooltip';
import { type DraftPickItem, getDraftData } from './api-calls';

// ── Constants ─────────────────────────────────────────────────────────────────

const posMeta: Record<string, { bg: string; tc: string }> = {
  QB: { bg: '#EEEDFE', tc: '#3C3489' },
  RB: { bg: '#E1F5EE', tc: '#085041' },
  WR: { bg: '#FAECE7', tc: '#712B13' },
  TE: { bg: '#FAEEDA', tc: '#633806' },
  K: { bg: '#F1EFE8', tc: '#444441' },
  'D/ST': { bg: '#E6F1FB', tc: '#0C447C' },
};

// ── Types ─────────────────────────────────────────────────────────────────────

type DraftResult =
  | { ok: true; data: DraftPickItem[] }
  | { ok: false; error: string };

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

function grade(pick: DraftPickItem): { g: string; cls: string; score: number } {
  const d = pick.draft_rank_delta;
  const r = pick.drafted_position_rank;

  if (r <= 5) {
    if (d >= 3)  return { g: 'A', cls: 'grade-a', score: 95 };
    if (d >= -1) return { g: 'B', cls: 'grade-b', score: 85 };
    if (d >= -4) return { g: 'C', cls: 'grade-c', score: 75 };
    if (d >= -6) return { g: 'D', cls: 'grade-d', score: 65 };
    return             { g: 'F', cls: 'grade-f', score: 55 };
  }

  if (r <= 14) {
    if (d >= 5)  return { g: 'A', cls: 'grade-a', score: 95 };
    if (d >= -2) return { g: 'B', cls: 'grade-b', score: 85 };
    if (d >= -5) return { g: 'C', cls: 'grade-c', score: 75 };
    if (d >= -9) return { g: 'D', cls: 'grade-d', score: 65 };
    return             { g: 'F', cls: 'grade-f', score: 55 };
  }

  // Deep picks (rank 15+): speculative, no F
  if (d >= 8)  return { g: 'A', cls: 'grade-a', score: 95 };
  if (d >= 0)  return { g: 'B', cls: 'grade-b', score: 85 };
  if (d >= -5) return { g: 'C', cls: 'grade-c', score: 75 };
  return             { g: 'D', cls: 'grade-d', score: 65 };
}

function getAlts(pick: DraftPickItem, allPicks: DraftPickItem[]): DraftPickItem[] {
  return allPicks
    .filter(
      (a) =>
        a.position === pick.position &&
        a.overall_pick_number > pick.overall_pick_number &&
        a.round <= pick.round + 2 &&
        a.player_name !== pick.player_name &&
        a.total_points > pick.total_points,
    )
    .sort((a, b) => b.total_points - a.total_points)
    .slice(0, 2);
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DraftRecapSkeleton() {
  return (
    <div className="p-6 max-w-250 mx-auto">
      <div className="flex items-center gap-2.5 mb-6">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-8 w-24 ml-2" />
        <Skeleton className="h-8 w-36" />
      </div>
      <div className="grid grid-cols-4 gap-2.5 mb-6">
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
    return [...seen.values()];
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
        grade(p).score > grade(best).score ? p : best,
      )
    : null;

  const maxRound = allPicks.length ? Math.max(...allPicks.map((p) => p.round)) : 0;
  const busts = picks.filter((p) => p.draft_rank_delta <= -10 && p.round <= maxRound - 4).length;
  const steals = picks.filter((p) => p.draft_rank_delta >= 5).length;

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
      <div className="flex items-center gap-2.5 mb-6 flex-wrap">
        <span className="text-[12px] font-medium text-muted-foreground">Season</span>
        <select
          className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
          value={selectedSeason}
          onChange={(e) => onSeasonChange(e.target.value)}
        >
          {[...seasons].sort((a, b) => Number(b) - Number(a)).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-[12px] font-medium text-muted-foreground ml-2">Manager</span>
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

      {/* Stat Strip */}
      <div className="grid grid-cols-4 gap-2.5 mb-6">
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Total VORP
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {picks.length ? totalVorp.toFixed(1) : '—'}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Best pick
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
            Steals
          </div>
          <div className="text-[22px] font-medium" style={{ color: '#27500A' }}>
            {steals}
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Busts
          </div>
          <div className="text-[22px] font-medium" style={{ color: '#791F1F' }}>
            {busts}
          </div>
        </div>
      </div>

      {/* Picks Table */}
      <div className="bg-card border border-border/50 rounded-lg mb-6">
        <div className="overflow-y-auto max-h-[calc(100vh-300px)]">
        <table className="w-full border-separate border-spacing-0 table-fixed text-[12px]">
          <thead className="sticky top-0 z-10">
            <tr>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50" style={{ width: '28px' }}>
                #
              </th>
              <th className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-2.5 text-left bg-muted border-b border-border/50" style={{ width: '180px' }}>
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
              const pm = posMeta[pick.position] ?? { bg: '#F1EFE8', tc: '#444441' };
              const delta = pick.draft_rank_delta;
              const deltaStr = (delta >= 0 ? '+' : '') + delta;
              const dpillCls = delta >= 3 ? 'delta-pos' : delta <= -3 ? 'delta-neg' : 'delta-neu';
              const { g } = grade(pick);
              const isBust = delta <= -10 && pick.round <= maxRound - 4;
              const alts = isBust ? getAlts(pick, allPicks) : [];
              const bustKey = `${selectedManager}-${selectedSeason}-${i}`;
              const isOpen = !!openBusts[bustKey];

              return (
                <React.Fragment key={pick.pick_id}>
                  <tr>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5 text-muted-foreground text-[11px]">{i + 1}</div>
                    </td>
                    <td className="border-b border-border/50">
                      <div className="px-3 py-2.5">
                        <div className="text-[13px] font-medium text-foreground flex items-center gap-1">
                          {pick.player_name}
                          {pick.draft_rank_delta >= 5 && <Gem className="w-3 h-3 shrink-0" style={{ color: '#27500A' }} />}
                          {pick.draft_rank_delta <= -10 && pick.round <= maxRound - 4 && <X className="w-3 h-3 shrink-0" style={{ color: '#791F1F' }} />}
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
                        <div className="px-3 py-2.5 text-center text-[13px] font-medium" style={{ color: pick.vorp >= 0 ? '#27500A' : '#791F1F' }}>
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
                            background: dpillCls === 'delta-pos' ? '#EAF3DE' : dpillCls === 'delta-neg' ? '#FCEBEB' : '#F1EFE8',
                            color: dpillCls === 'delta-pos' ? '#27500A' : dpillCls === 'delta-neg' ? '#791F1F' : '#444441',
                          }}
                        >
                          {deltaStr} places
                        </span>
                      </div>
                    </td>
                  </tr>
                  {(g === 'D' || g === 'F') && alts.length > 0 && (
                    <tr>
                      <td colSpan={8} className="p-0">
                        <div className="bg-muted/50 border-t border-border/50 p-2.5 flex flex-col gap-1.5">
                          <div className="flex items-center justify-between mb-1">
                            <div className="text-[10px] font-medium uppercase tracking-[0.06em]" style={{ color: '#791F1F' }}>
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
                                const altPm = posMeta[alt.position] ?? { bg: '#F1EFE8', tc: '#444441' };
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
                                      style={{ background: '#EAF3DE', color: '#27500A' }}
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
      </div>
    </TooltipProvider>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DraftRecap() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as 'ESPN' | 'SLEEPER';

  const seasons: string[] = useMemo(() => {
    try {
      return JSON.parse(getCookie('leagueSeasons')) as string[];
    } catch {
      return [];
    }
  }, []);

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
    <div className="p-6 max-w-250 mx-auto">
      <Suspense fallback={<DraftRecapSkeleton />}>
        <DraftRecapContent
          promise={draftPromise}
          seasons={seasons}
          selectedSeason={selectedSeason}
          onSeasonChange={setSelectedSeason}
        />
      </Suspense>
    </div>
  );
}
