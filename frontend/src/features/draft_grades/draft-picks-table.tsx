import { ChevronDown, Gem, Info, X } from 'lucide-react';
import { Fragment } from 'react';

import { type DraftPickItem } from './api-calls';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DELTA_PILL_NEG,
  DELTA_PILL_POS,
  GREEN,
  GREEN_BG,
  RED,
  RED_BG,
  STEAL_DELTA_MIN,
} from '@/features/draft_grades/constants';
import { type BustWithAlts } from '@/features/draft_grades/types';
import { POSITION_COLORS, positionColorMeta } from '@/lib/color-constants';

export function DraftPicksTable({
  picks,
  selectedManager,
  selectedSeason,
  isAuction,
  isBustPick,
  bustsWithAltsMap,
  openBusts,
  toggleBust,
  pickLabel,
  fmtBid,
}: {
  picks: DraftPickItem[];
  selectedManager: string;
  selectedSeason: string;
  isAuction: boolean;
  isBustPick: (pick: DraftPickItem) => boolean;
  bustsWithAltsMap: Map<string, BustWithAlts>;
  openBusts: Record<string, boolean>;
  toggleBust: (key: string) => void;
  pickLabel: (pick: DraftPickItem) => string;
  fmtBid: (n: number) => string;
}) {
  return (
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
                              (alt.total_points ?? 0) - (pick.total_points ?? 0)
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
  );
}
