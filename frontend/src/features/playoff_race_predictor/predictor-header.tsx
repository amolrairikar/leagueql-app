import { Check, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';

import {
  type PickableMatchup,
  type Picks,
  type PredictorModel,
} from './compute-projection';

import { cn } from '@/lib/utils';

export function PredictorHeader({
  canReset,
  onReset,
}: {
  canReset: boolean;
  onReset: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">
          Playoff Picture
        </h2>
        <p className="text-[13px] text-muted-foreground mt-1 max-w-[62ch]">
          The bracket isn&apos;t set yet — the regular season is still in
          progress. Pick the winners of the remaining games to project who makes
          the playoffs.
        </p>
      </div>
      <button
        type="button"
        onClick={onReset}
        disabled={!canReset}
        className="inline-flex items-center gap-1.5 text-[13px] font-medium px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted disabled:opacity-45 disabled:hover:bg-card whitespace-nowrap cursor-pointer disabled:cursor-default"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        Reset picks
      </button>
    </div>
  );
}

export function WeekStepper({
  model,
  picks,
  activeIdx,
  onSelect,
}: {
  model: PredictorModel;
  picks: Picks;
  activeIdx: number;
  onSelect: (idx: number) => void;
}) {
  const active = Math.min(activeIdx, model.weeks.length - 1);
  const pickedInWeek = (m: PickableMatchup[]) =>
    m.filter((mm) => picks[mm.key]).length;

  return (
    <div className="flex items-center gap-2 mb-4">
      <button
        type="button"
        aria-label="Previous week"
        disabled={active === 0}
        onClick={() => onSelect(active - 1)}
        className="w-8 h-8 rounded-lg border border-border bg-card grid place-items-center hover:bg-muted disabled:opacity-40 disabled:hover:bg-card cursor-pointer disabled:cursor-default"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <div className="flex gap-1.5 overflow-x-auto">
        {model.weeks.map((w, i) => {
          const done = pickedInWeek(w.matchups);
          const complete = done === w.matchups.length;
          return (
            <button
              key={w.week}
              type="button"
              onClick={() => onSelect(i)}
              className={cn(
                'flex flex-col items-center gap-0.5 min-w-[74px] px-3 py-1 rounded-lg border cursor-pointer',
                i === active
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-card hover:bg-muted',
              )}
            >
              <span
                className={cn(
                  'text-[13px] font-semibold whitespace-nowrap',
                  i === active ? 'text-primary' : 'text-foreground',
                )}
              >
                Week {w.week}
              </span>
              <span className="text-[10px] text-muted-foreground inline-flex items-center gap-1">
                {complete && (
                  <Check className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" />
                )}
                {done}/{w.matchups.length}
              </span>
            </button>
          );
        })}
      </div>
      <button
        type="button"
        aria-label="Next week"
        disabled={active === model.weeks.length - 1}
        onClick={() => onSelect(active + 1)}
        className="w-8 h-8 rounded-lg border border-border bg-card grid place-items-center hover:bg-muted disabled:opacity-40 disabled:hover:bg-card cursor-pointer disabled:cursor-default"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
