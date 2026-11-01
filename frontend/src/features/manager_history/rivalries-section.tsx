import { Info } from 'lucide-react';

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DOMINATION_WIN_RATE,
  NEMESIS_WIN_RATE,
} from '@/features/manager_history/process-data';
import { type ManagerData } from '@/features/manager_history/types';
import {
  NEMESIS_COLORS,
  POSITION_COLORS,
  UI_COLORS,
} from '@/lib/color-constants';
import { pct } from '@/lib/utils';

export function RivalriesSection({ m }: { m: ManagerData }) {
  const sorted = [...m.rivalries].sort((a, b) => {
    const aRate = a.w + a.l > 0 ? a.w / (a.w + a.l) : 0;
    const bRate = b.w + b.l > 0 ? b.w / (b.w + b.l) : 0;
    return bRate - aRate;
  });
  const best = sorted
    .filter((r) => r.w + r.l > 0 && r.w / (r.w + r.l) >= DOMINATION_WIN_RATE)
    .slice(0, 2);
  const worst = [...sorted]
    .reverse()
    .filter((r) => r.w + r.l > 0 && r.w / (r.w + r.l) < NEMESIS_WIN_RATE)
    .slice(0, 2);
  const closest = [...m.rivalries]
    .sort((a, b) => {
      const aDiff = Math.abs(a.avgFor - a.avgAgainst);
      const bDiff = Math.abs(b.avgFor - b.avgAgainst);
      return aDiff - bDiff;
    })
    .slice(0, 2);

  return (
    <>
      {m.rivalries.length >= 3 && (
        <>
          <div className="flex items-center gap-1.5 mb-2.5">
            <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
              Rivalries
            </p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 text-muted-foreground cursor-default" />
                </TooltipTrigger>
                <TooltipContent
                  side="right"
                  className="max-w-72 bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
                >
                  <div className="flex flex-col gap-2.5">
                    <p className="text-[12px] leading-relaxed">
                      <span className="font-semibold">Domination</span>
                      {` — opponents where your head-to-head win percentage is ${Math.round(DOMINATION_WIN_RATE * 100)}% or higher. You've consistently had their number and rarely lose this matchup.`}
                    </p>
                    <p className="text-[12px] leading-relaxed">
                      <span className="font-semibold">Nemesis</span>
                      {` — opponents where your head-to-head win percentage is below ${Math.round(NEMESIS_WIN_RATE * 100)}%. No matter how well you play, this opponent tends to come out on top.`}
                    </p>
                    <p className="text-[12px] leading-relaxed">
                      <span className="font-semibold">Rival</span>
                      {` — the opponent with the smallest average scoring margin between you. These are your most evenly matched games, often decided by just a handful of points.`}
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            {[
              ...best.map((r) => ({ r, type: 'best' as const })),
              ...worst.map((r) => ({ r, type: 'worst' as const })),
              ...(closest[0]
                ? [{ r: closest[0], type: 'closest' as const }]
                : []),
            ].map(({ r, type }) => {
              const total = r.w + r.l;
              const winRate = total > 0 ? (r.w / total).toFixed(3) : '0.000';
              const fillPct = pct(r.w, r.l);
              let typeBadge, typeColor;
              if (type === 'best') {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{
                      background: POSITION_COLORS.RB.bg,
                      color: POSITION_COLORS.RB.tc,
                    }}
                  >
                    Domination
                  </span>
                );
                typeColor = POSITION_COLORS.RB.color;
              } else if (type === 'worst') {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{
                      background: NEMESIS_COLORS.bg,
                      color: NEMESIS_COLORS.text,
                    }}
                  >
                    Nemesis
                  </span>
                );
                typeColor = NEMESIS_COLORS.accent;
              } else {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{
                      background: POSITION_COLORS.TE.bg,
                      color: POSITION_COLORS.TE.tc,
                    }}
                  >
                    Rival
                  </span>
                );
                typeColor = POSITION_COLORS.TE.color;
              }
              const margin = (r.avgFor - r.avgAgainst).toFixed(1);
              const marginSign = parseFloat(margin) > 0 ? '+' : '';
              return (
                <div
                  key={r.oppId}
                  className="bg-card border border-border/50 rounded-lg p-3.5 flex flex-col gap-2.5"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-medium text-white shrink-0"
                      style={{ background: r.oppColor }}
                    >
                      {r.oppInit}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium text-foreground">
                        {r.oppName}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {r.oppTeam || `Team ${r.oppName}`}
                      </div>
                    </div>
                    <div className="shrink-0">{typeBadge}</div>
                  </div>
                  <div>
                    <div className="flex items-baseline gap-1.5 mb-1.5">
                      <span
                        className="text-[18px] font-medium"
                        style={{ color: typeColor }}
                      >
                        {r.w}-{r.l}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {winRate} win percentage
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden flex-1">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${fillPct}%`,
                            background: typeColor,
                          }}
                        />
                      </div>
                      <span className="text-[11px] text-muted-foreground whitespace-nowrap">
                        {total} games
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg for
                      </div>
                      <div className="text-[13px] font-medium text-foreground">
                        {r.avgFor.toFixed(1)}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg against
                      </div>
                      <div className="text-[13px] font-medium text-foreground">
                        {r.avgAgainst.toFixed(1)}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg margin
                      </div>
                      <div
                        className="text-[13px] font-medium"
                        style={{
                          color:
                            parseFloat(margin) >= 0
                              ? UI_COLORS.positive
                              : UI_COLORS.negative,
                        }}
                      >
                        {marginSign}
                        {margin}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Last game
                      </div>
                      <div
                        className="text-[13px] font-medium"
                        style={{
                          color:
                            r.lastResult === 'W'
                              ? UI_COLORS.positive
                              : UI_COLORS.negative,
                        }}
                      >
                        {r.lastResult}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}
