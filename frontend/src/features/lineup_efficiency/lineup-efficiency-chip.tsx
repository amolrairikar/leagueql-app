import { Sparkles } from 'lucide-react';
import { useState } from 'react';

import {
  computeStartSitReport,
  type StartSitReport,
} from './compute-lineup-efficiency';

import type { BoxScoreSide } from '@/components/box-score-card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

/**
 * Lineup-efficiency chip shown under a team's name in the box score (frontend/lineup-efficiency). It
 * reads `⚡ {pct}% efficient` and opens a slot-by-slot start/sit report of the
 * points the manager left on the bench.
 *
 * It is a free feature; the only reason it renders nothing is when there is no
 * bench data to measure (ESPN seasons before 2018).
 */
export function LineupEfficiencyChip({
  side,
  week,
}: {
  side: BoxScoreSide;
  week?: string;
}) {
  const report = computeStartSitReport(side.starters, side.bench);
  // No bench means efficiency can't be measured (e.g. ESPN seasons < 2018).
  if (!report.hasBenchData) return null;

  return (
    <LineupEfficiencyChipInner
      report={report}
      ownerUsername={side.ownerUsername}
      week={week}
    />
  );
}

function LineupEfficiencyChipInner({
  report,
  ownerUsername,
  week,
}: {
  report: StartSitReport;
  ownerUsername: string;
  week?: string;
}) {
  const [open, setOpen] = useState(false);

  const pct = Math.round(report.efficiencyPct * 100);
  const mistakes = report.rows.filter((r) => r.delta > 0);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
      >
        <Sparkles className="w-3 h-3 shrink-0" />
        <span className="tabular-nums">{pct}% efficient</span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              Start/Sit Report
            </DialogTitle>
            <DialogDescription>
              {ownerUsername}
              {week ? ` · Week ${week}` : ''}
            </DialogDescription>
          </DialogHeader>

          {mistakes.length === 0 ? (
            <p className="text-[13px] text-muted-foreground py-4">
              Perfect lineup — nothing left on the bench. This manager captured{' '}
              {pct}% of their possible points.
            </p>
          ) : (
            <div>
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                    <th className="py-2 pr-2">Slot</th>
                    <th className="py-2 pr-2">Started</th>
                    <th className="py-2 pr-2">Optimal</th>
                    <th className="py-2 text-right" />
                  </tr>
                </thead>
                <tbody>
                  {mistakes.map((row, i) => (
                    <tr key={i} className="border-t border-border/50">
                      <td className="py-2 pr-2 text-[11px] font-medium text-muted-foreground">
                        {row.slot}
                      </td>
                      <td className="py-2 pr-2 text-foreground">
                        {row.started
                          ? `${row.started.name} (${row.started.points.toFixed(2)})`
                          : '—'}
                      </td>
                      <td className="py-2 pr-2 text-foreground">
                        {row.optimal
                          ? `${row.optimal.name} (${row.optimal.points.toFixed(2)})`
                          : '—'}
                      </td>
                      <td className="py-2 text-right tabular-nums text-destructive">
                        +{row.delta.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[12px] text-muted-foreground">
                Left{' '}
                <span className="font-medium text-foreground tabular-nums">
                  {report.pointsLeft.toFixed(2)}
                </span>{' '}
                on the bench ·{' '}
                <span className="font-medium text-foreground tabular-nums">
                  {pct}%
                </span>{' '}
                efficient
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
