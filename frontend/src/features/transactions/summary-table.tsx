import { use } from 'react';

import { TeamAvatar } from '@/components/team-avatar';
import { buildOwnerSummary } from '@/features/transactions/owner-summary';
import {
  type StandingsResult,
  type TransactionsResult,
} from '@/features/transactions/types';
import {
  buildStandingsVisuals,
  type OwnerVisual,
} from '@/features/transactions/visuals';
import { avatarColor } from '@/lib/color-constants';

export function SummaryTable({
  promise,
  standingsPromise,
}: {
  promise: Promise<TransactionsResult>;
  standingsPromise: Promise<StandingsResult>;
}) {
  const result = use(promise);
  const standingsResult = use(standingsPromise);

  // The wire below renders the error / empty state, so the table stays out of the way.
  if (!result.ok) return null;
  const rows = buildOwnerSummary(result.data);
  if (rows.length === 0) return null;

  // Reuse the Season Standings avatar/color when standings is available; fall back to the
  // row's own index + initials when it isn't (e.g. a season with no standings yet, or a
  // roster not present in standings).
  const visuals = standingsResult.ok
    ? buildStandingsVisuals(standingsResult.data)
    : new Map<string, OwnerVisual>();
  const maxTotal = Math.max(...rows.map((r) => r.total), 1);

  const headCell =
    'text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted';

  return (
    <div className="bg-card border border-border/50 rounded-xl overflow-hidden shadow-sm">
      <div className="max-h-[70vh] overflow-auto">
        <table
          className="w-full border-collapse text-[13px]"
          style={{ tableLayout: 'fixed', minWidth: '480px' }}
        >
          <thead className="sticky top-0 z-20">
            <tr>
              <th
                className={`${headCell} text-left sticky left-0 z-10`}
                style={{ width: '40%' }}
              >
                Owner
              </th>
              <th className={`${headCell} text-right`}>Waivers</th>
              <th className={`${headCell} text-right`}>Free Agents</th>
              <th className={`${headCell} text-right`}>Trades</th>
              <th className={`${headCell} text-right`}>Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const visual = visuals.get(row.rosterId);
              return (
                <tr
                  key={row.rosterId}
                  className="border-b border-border/50 last:border-0 bg-card"
                >
                  <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
                    <div className="flex items-center gap-2">
                      <TeamAvatar
                        teamLogo={visual?.teamLogo ?? null}
                        teamName={row.teamName}
                        ownerUsername={row.ownerUsername}
                        color={avatarColor(visual?.colorIndex ?? i)}
                      />
                      <div className="flex flex-col">
                        <span className="text-[13px] font-medium text-foreground">
                          {row.ownerUsername}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          {row.teamName}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.waiver}
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.free_agent}
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.trade}
                  </td>
                  <td className="px-3.5 py-2.5 text-right">
                    <span className="inline-flex items-center justify-end gap-2">
                      <span className="hidden sm:block h-1.5 w-12 rounded-full bg-muted overflow-hidden">
                        <span
                          className="block h-full rounded-full bg-primary"
                          style={{
                            width: `${Math.round((row.total / maxTotal) * 100)}%`,
                          }}
                        />
                      </span>
                      <span className="font-semibold text-foreground tabular-nums">
                        {row.total}
                      </span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
