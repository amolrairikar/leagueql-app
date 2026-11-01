import { ChevronDown, X } from 'lucide-react';

import { type DraftPickItem } from './api-calls';

import { GREEN, GREEN_BG, RED } from '@/features/draft_grades/constants';
import { type BustWithAlts } from '@/features/draft_grades/types';
import { positionColorMeta } from '@/lib/color-constants';

export function BustAlternatives({
  bustsWithAlts,
  openBusts,
  toggleBust,
  pickLabel,
  isAuction,
  fmtBid,
}: {
  bustsWithAlts: BustWithAlts[];
  openBusts: Record<string, boolean>;
  toggleBust: (key: string) => void;
  pickLabel: (pick: DraftPickItem) => string;
  isAuction: boolean;
  fmtBid: (n: number) => string;
}) {
  return (
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
  );
}
