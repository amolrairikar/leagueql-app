import { CalendarClock } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useIsOwner } from '@/features/ownership/use-is-owner';
import { useSeasonStaleness } from '@/features/sidebar/use-season-staleness';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

/**
 * Tells a Sleeper league's owner to onboard the current season's league ID when
 * the current fantasy season is after the league's latest onboarded season
 * (frontend/sleeper-stale-season-banner). Rendered below the in-app header.
 * Sleeper links seasons backward-only, so refreshing the existing league can
 * never surface the new season — the owner must re-onboard from the landing
 * page. Shows only for Sleeper leagues, only to the owner, and only while the
 * league's latest season is behind the current one; it is not dismissible and
 * disappears once a current-season league is onboarded.
 */
export function SleeperStaleSeasonBanner() {
  const { platform, leagueId } = getLeagueCookies();
  const { loading: ownerLoading, isOwner } = useIsOwner();
  const { isStaleSeason } = useSeasonStaleness();

  // Bail before reading server state for the cases that never show the banner:
  // demo mode, no connected league, or an ESPN league.
  if (isDemoMode() || !leagueId || platform !== 'SLEEPER') return null;

  // Wait for ownership before deciding; only owners can re-onboard the league.
  if (ownerLoading || !isOwner || !isStaleSeason) return null;

  return (
    <div className="flex h-8 shrink-0 items-center justify-center gap-2 border-b border-primary/50 bg-primary/40 px-4">
      <CalendarClock className="size-3.5 text-white" aria-hidden="true" />
      <span className="text-[0.72rem] font-medium tracking-wide text-white">
        Not seeing your current season&apos;s data? Enter your latest
        season&apos;s league ID on the{' '}
        <Link to="/" className="underline underline-offset-2">
          landing page
        </Link>
        .
      </span>
    </div>
  );
}
