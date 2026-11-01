import { Info } from 'lucide-react';

import { type DraftPickItem } from './api-calls';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  AUCTION_BUST_MIN_BID,
  GREEN,
  RED,
} from '@/features/draft_grades/constants';

export function DraftStatStrip({
  bestPick,
  worstPick,
  steals,
  busts,
  isAuction,
  pickLabel,
  fmtBid,
}: {
  bestPick: DraftPickItem | null;
  worstPick: DraftPickItem | null;
  steals: number;
  busts: number;
  isAuction: boolean;
  pickLabel: (pick: DraftPickItem) => string;
  fmtBid: (n: number) => string;
}) {
  return (
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
                The player who most underperformed their drafted position rank —
                the pick with the lowest rank delta. K and D/ST are excluded.
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
                A steal is a player whose actual finish at their position was 5
                or more spots better than where they were drafted.
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
  );
}
