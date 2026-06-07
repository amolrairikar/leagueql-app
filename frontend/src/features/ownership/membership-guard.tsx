import { ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getLeague, verifyMembership } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { ApiError, clearApiCache } from '@/lib/api-client';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import { EspnExtensionError, requestEspnCookies } from '@/lib/espn-extension';

type GateState = 'loading' | 'ok' | 'denied';

/**
 * Member-gates ESPN league views (LQL-01 / BE-016 / FE-025). ESPN league data is
 * confidential, so a non-member's `GET /leagues/{id}` returns 403; this guard
 * detects that and renders a verification prompt instead of the page. Sleeper
 * reads stay open, so the guard resolves to `ok` for them. Any non-403 failure is
 * fail-open (the backend stays the source of truth and the page surfaces its own
 * error inline).
 */
export function MembershipGuard({ children }: { children: React.ReactNode }) {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [gate, setGate] = useState<GateState>(bypass ? 'ok' : 'loading');

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform as Platform)
      .then(() => {
        if (!cancelled) setGate('ok');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setGate(
          err instanceof ApiError && err.status === 403 ? 'denied' : 'ok',
        );
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  if (gate === 'loading') {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );
  }

  if (gate === 'denied') {
    return (
      <VerifyMembershipPrompt
        leagueId={leagueId}
        platform={platform as Platform}
        onVerified={() => {
          // Membership now grants access; drop cached 403 reads so the page and
          // the subscription/owner hooks re-fetch a 200.
          clearApiCache();
          setGate('ok');
        }}
      />
    );
  }

  return <>{children}</>;
}

/**
 * Prompt shown to a non-member of an ESPN league. Uses the Chrome extension to
 * fill the caller's ESPN cookies and posts them to `verify-membership`; on
 * success the caller becomes a member and the page is shown.
 */
export function VerifyMembershipPrompt({
  leagueId,
  platform,
  onVerified,
}: {
  leagueId: string;
  platform: Platform;
  onVerified: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleVerify() {
    setLoading(true);
    setError(null);
    try {
      const { swid, espnS2 } = await requestEspnCookies();
      await verifyMembership(leagueId, platform, { swid, s2: espnS2 });
      onVerified();
    } catch (err) {
      if (err instanceof EspnExtensionError) {
        setError(
          err.reason === 'not_logged_in'
            ? 'Log into ESPN in your browser, then try again.'
            : 'Could not reach the ESPN extension. Please install it and try again.',
        );
      } else if (err instanceof ApiError && err.status === 403) {
        setError("We couldn't confirm you're in this ESPN league.");
      } else {
        setError(
          err instanceof Error ? err.message : 'Failed to verify membership.',
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <ShieldCheck className="size-6 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold">Verify your ESPN league membership</h1>
      <p className="text-muted-foreground max-w-md">
        ESPN league data is private. Verify your ESPN cookies to confirm
        you&apos;re in this league and unlock its dashboard.
      </p>
      <Button
        className="cursor-pointer"
        disabled={loading}
        onClick={() => void handleVerify()}
      >
        {loading && <Spinner className="size-4" />}
        Verify membership
      </Button>
      {error && <ErrorAlert message={error} className="max-w-md text-left" />}
    </div>
  );
}
