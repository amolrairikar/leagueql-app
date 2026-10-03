import { KeyRound } from 'lucide-react';

import { useIsOwner } from '@/features/ownership/use-is-owner';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

/**
 * Tells an ESPN league's owner that automatic refresh is paused because ESPN
 * rejected their saved cookies (frontend/refresh-reminder-banner). ESPN cookies
 * expire and can't be renewed for the owner, so a scheduled refresh that ESPN
 * rejects flags the stored cookies (backend/espn-credential-storage) and the
 * league metadata reports `espn_reauth_required`. The banner points at the
 * sidebar's Update ESPN Cookies action; it is not dismissible and disappears once
 * the owner re-enters cookies (re-storing them clears the flag).
 */
export function EspnReauthBanner() {
  const { platform, leagueId } = getLeagueCookies();
  const { loading, isOwner, espnReauthRequired } = useIsOwner();

  if (isDemoMode() || !leagueId || platform !== 'ESPN') return null;
  // The backend only reports re-auth to the owner; isOwner keeps the gate explicit.
  if (loading || !isOwner || !espnReauthRequired) return null;

  return (
    <div
      role="alert"
      className="flex min-h-8 shrink-0 items-center justify-center gap-2 border-b border-destructive/50 bg-destructive/80 px-4 py-1"
    >
      <KeyRound className="size-3.5 shrink-0 text-white" aria-hidden="true" />
      <span className="text-[0.72rem] font-medium tracking-wide text-white">
        ESPN rejected your saved cookies, so automatic refresh is paused. Click
        &quot;Update ESPN Cookies&quot; in the sidebar to resume.
      </span>
    </div>
  );
}
