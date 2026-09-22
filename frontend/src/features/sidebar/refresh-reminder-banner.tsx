import { RefreshCw } from 'lucide-react';

import { useIsOwner } from '@/features/ownership/use-is-owner';
import { useLeagueFreshness } from '@/features/ownership/use-league-freshness';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

/**
 * Reminds an ESPN league's owner to refresh when the data is more than 7 days old
 * (frontend/refresh-reminder-banner). Rendered below the in-app header. Shows only
 * for ESPN leagues that are not enrolled in auto-refresh, only to the owner, and only
 * while the data is stale — it is not dismissible and disappears on its own once the
 * league is refreshed. An ESPN league opted into auto-refresh (auto_refresh_enabled)
 * refreshes on its own and hides the sidebar's Refresh League action, so it gets no
 * nudge here. Sleeper and Yahoo also need no reminder (Sleeper always auto-refreshes;
 * an opted-in Yahoo league refreshes on its stored OAuth token).
 */
export function RefreshReminderBanner() {
  const { platform, leagueId } = getLeagueCookies();
  const { loading: ownerLoading, isOwner, autoRefreshEnabled } = useIsOwner();
  const { loading: freshnessLoading, isStale } = useLeagueFreshness();

  // Bail before reading server state for the cases that never show the banner:
  // demo mode, no connected league, or a Sleeper league.
  if (isDemoMode() || !leagueId || platform !== 'ESPN') return null;

  // Wait for ownership + freshness before deciding; only owners see the sidebar's
  // Refresh League action the message points at, and an auto-refresh-enabled league
  // has no such action (it refreshes on a schedule), so it gets no reminder.
  if (
    ownerLoading ||
    freshnessLoading ||
    !isOwner ||
    !isStale ||
    autoRefreshEnabled
  )
    return null;

  return (
    <div className="flex h-8 shrink-0 items-center justify-center gap-2 border-b border-primary/50 bg-primary/40 px-4">
      <RefreshCw className="size-3.5 text-white" aria-hidden="true" />
      <span className="text-[0.72rem] font-medium tracking-wide text-white">
        Refresh your ESPN league data by clicking the &quot;Refresh League&quot;
        button in the sidebar!
      </span>
    </div>
  );
}
