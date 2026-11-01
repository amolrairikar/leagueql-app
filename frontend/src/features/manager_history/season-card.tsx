import { ChevronDown } from 'lucide-react';
import { useId, useState } from 'react';

import { ordinal } from '@/features/manager_history/format';
import { resultBadge } from '@/features/manager_history/result-badge';
import { SeasonSchedulePanel } from '@/features/manager_history/season-schedule-panel';
import { type SeasonEntry } from '@/features/manager_history/types';
import { type Platform } from '@/lib/cookie-handler';

export function SeasonCard({
  season: s,
  managerColor,
  username,
  platform,
}: {
  season: SeasonEntry;
  managerColor: string;
  username: string;
  platform: Platform;
}) {
  const [open, setOpen] = useState(false);
  const headerId = useId();
  const panelId = useId();
  const expandable = s.schedule.length > 0;

  return (
    <div
      className={`bg-card rounded-lg overflow-hidden ${
        s.result === 'champion' ? 'border-2' : 'border border-border/50'
      }`}
      style={s.result === 'champion' ? { borderColor: managerColor } : {}}
    >
      <button
        id={headerId}
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={!expandable}
        aria-expanded={expandable ? open : undefined}
        aria-controls={expandable ? panelId : undefined}
        className="w-full text-left p-3.5 grid grid-cols-1 sm:grid-cols-[80px_1fr_auto] gap-3 items-start sm:items-center transition-colors enabled:cursor-pointer enabled:hover:bg-accent/40 disabled:cursor-default"
      >
        <div>
          <div className="text-[13px] font-medium text-foreground">
            {s.year}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {s.team || `Team ${username}`}
          </div>
          {s.result && <div className="mt-2">{resultBadge(s.result)}</div>}
        </div>
        <div className="flex gap-5 flex-wrap">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
              Record
            </div>
            <div className="text-[14px] font-medium text-foreground">
              {s.record}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
              Total pts
            </div>
            <div className="text-[14px] font-medium text-foreground">
              {s.pts.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              })}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
              Avg / wk
            </div>
            <div className="text-[14px] font-medium text-foreground">
              {s.avg.toFixed(1)}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
              High score
            </div>
            <div className="text-[14px] font-medium text-foreground">
              {s.high.toFixed(2)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex sm:flex-col items-center sm:items-end gap-1.5 sm:gap-1.5">
            <div className="text-[20px] font-medium text-foreground">
              {s.finish != null ? ordinal(s.finish) : '—'}
            </div>
            <div className="text-[11px] text-muted-foreground">place</div>
          </div>
          {expandable && (
            <ChevronDown
              aria-hidden
              className="w-4 h-4 text-muted-foreground transition-transform ml-auto sm:ml-0"
              style={{ transform: open ? 'rotate(180deg)' : 'none' }}
            />
          )}
        </div>
      </button>
      {open && (
        <div
          id={panelId}
          role="region"
          aria-labelledby={headerId}
          className="border-t border-border/50 p-3.5"
        >
          <SeasonSchedulePanel season={s} platform={platform} />
        </div>
      )}
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────
