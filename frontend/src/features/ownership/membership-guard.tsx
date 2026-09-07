import { ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api-client';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

type GateState = 'loading' | 'ok' | 'denied';

/**
 * Member-gates ESPN league views (backend/league-authorization / frontend/ownership-transfer). ESPN league data is
 * confidential, so a non-member's `GET /leagues/{id}` returns 403; this guard
 * detects that and directs the caller to obtain an invite link from the league
 * owner (the invite link is the only non-owner join path) instead of rendering the
 * page. Sleeper reads stay open, so the guard resolves to `ok` for them. Any
 * non-403 failure is fail-open (the backend stays the source of truth and the page
 * surfaces its own error inline).
 */
export function MembershipGuard({ children }: { children: React.ReactNode }) {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;
  const navigate = useNavigate();

  const [gate, setGate] = useState<GateState>(bypass ? 'ok' : 'loading');

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then(() => {
        if (!cancelled) setGate('ok');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 403) {
          setGate('denied');
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
        <h1 className="text-2xl font-bold">This ESPN league is private</h1>
        <p className="text-muted-foreground max-w-md">
          You&apos;re not a member of this league yet. Ask the league owner to
          share their invite link with you, then open that link to join and
          unlock the dashboard.
        </p>
        <Button
          className="cursor-pointer"
          onClick={() => void navigate('/connect_league')}
        >
          View another league
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}
