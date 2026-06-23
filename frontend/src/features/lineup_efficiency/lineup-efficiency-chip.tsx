import { Lock, Sparkles } from 'lucide-react';
import { useState } from 'react';

import {
  computeStartSitReport,
  type StartSitReport,
} from './compute-lineup-efficiency';

import type { BoxScoreSide } from '@/components/box-score-card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';
import { isDemoMode } from '@/lib/cookie-handler';
import { isBillingEnabled, isEnabled } from '@/lib/feature-flags';

const FEATURE_FLAG = 'premium_feature';
const FEATURE_LABEL = 'Lineup efficiency';

/**
 * Premium lineup-efficiency chip shown under a team's name in the box score
 * (FE-035). Unlocked it reads `⚡ {pct}% efficient` and opens a slot-by-slot
 * start/sit report; locked it reads `🔒 Lineup efficiency` and opens the paywall.
 *
 * Because it lives inside a shared, mostly-free component it gates via the
 * feature-flag/subscription primitives directly rather than wrapping
 * `SubscriptionGuard` (whose locked state is a full-section paywall). It renders
 * nothing when the `billing` master flag is off or when there is no bench data to
 * measure (ESPN seasons before 2018).
 */
export function LineupEfficiencyChip({
  side,
  week,
}: {
  side: BoxScoreSide;
  week?: string;
}) {
  // Premium system off → the feature doesn't exist yet; render nothing.
  if (!isBillingEnabled()) return null;
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
  const { loading, isActive } = useSubscription();

  const demo = isDemoMode();
  const gated = isEnabled(FEATURE_FLAG) && !demo;
  // While the subscription status is resolving we don't yet know if it's locked,
  // so show the neutral label rather than flashing the efficiency % to a
  // not-yet-confirmed subscriber.
  const pending = gated && loading;
  const locked = gated && !loading && !isActive;
  const showPercent = !locked && !pending;

  const pct = Math.round(report.efficiencyPct * 100);
  const mistakes = report.rows.filter((r) => r.delta > 0);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
      >
        {showPercent ? (
          <Sparkles className="w-3 h-3 shrink-0" />
        ) : (
          <Lock className="w-3 h-3 shrink-0" />
        )}
        {showPercent ? (
          <span className="tabular-nums">{pct}% efficient</span>
        ) : (
          <span>Lineup efficiency</span>
        )}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Start/Sit Report
              {demo && (
                <Badge variant="secondary">
                  <Sparkles />
                  Premium
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              {ownerUsername}
              {week ? ` · Week ${week}` : ''}
            </DialogDescription>
          </DialogHeader>

          {locked ? (
            <SubscriptionRequired featureLabel={FEATURE_LABEL} />
          ) : mistakes.length === 0 ? (
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
