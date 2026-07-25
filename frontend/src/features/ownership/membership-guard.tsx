import { ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { JoinLeagueDialog } from '@/features/connect_league/join-league-dialog';
import { ApiError, clearApiCache } from '@/lib/api-client';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

type GateState = 'loading' | 'ok' | 'denied';

/**
 * Member-gates ESPN league views (LQL-01 / BE-016 / FE-025). ESPN league data is
 * confidential, so a non-member's `GET /leagues/{id}` returns 403; this guard
 * detects that and prompts the caller to join via the shared `JoinLeagueDialog`
 * instead of rendering the page. Sleeper reads stay open, so the guard resolves to
 * `ok` for them. Any non-403 failure is fail-open (the backend stays the source of
 * truth and the page surfaces its own error inline).
 */
export function MembershipGuard({ children }: { children: React.ReactNode }) {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [gate, setGate] = useState<GateState>(bypass ? 'ok' : 'loading');
  const [joinOpen, setJoinOpen] = useState(false);

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform as Platform)
      .then(() => {
        if (!cancelled) setGate('ok');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 403) {
          setGate('denied');
          setJoinOpen(true);
        } else {
          setGate('ok');
        }
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
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="bg-muted flex size-12 items-center justify-center rounded-full">
          <ShieldCheck className="size-6 text-muted-foreground" />
        </div>
        <h1 className="text-2xl font-bold">
          Verify your ESPN league membership
        </h1>
        <p className="text-muted-foreground max-w-md">
          ESPN league data is private. Verify your ESPN cookies to confirm
          you&apos;re in this league and unlock its dashboard.
        </p>
        <Button className="cursor-pointer" onClick={() => setJoinOpen(true)}>
          Verify membership
        </Button>
        <JoinLeagueDialog
          open={joinOpen}
          onOpenChange={setJoinOpen}
          leagueId={leagueId}
          onJoined={() => {
            // Membership now grants access; drop cached 403 reads so the page and
            // the owner hooks re-fetch a 200, then render the page.
            clearApiCache();
            setGate('ok');
          }}
        />
      </div>
    );
  }

  return <>{children}</>;
}
