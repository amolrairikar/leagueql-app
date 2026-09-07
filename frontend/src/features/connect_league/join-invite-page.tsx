import { SignIn, useUser } from '@clerk/react';
import { Ticket } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import {
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom';

import { acceptInvite, getLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { ApiError } from '@/lib/api-client';
import { setLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

type JoinState = 'joining' | 'error';

/**
 * Invite-link redemption page (`/join/:leagueId`,
 * backend/league-authorization / frontend/ownership-transfer).
 *
 * A leaguemate opens the owner-shared link `/join/{leagueId}?platform=ESPN&invite={token}`.
 * If signed out, an embedded Clerk sign-in returns them to this same URL after
 * auth. Once signed in, the token is redeemed via `accept-invite` (no ESPN cookies
 * required); on success the caller is added to the league's members, the league
 * cookies are set, and they are routed to the dashboard. An invalid or revoked
 * token surfaces an inline error asking for a fresh link.
 */
export default function JoinInvitePage() {
  const { isSignedIn, isLoaded } = useUser();
  const { leagueId } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const platform = searchParams.get('platform') as Platform | null;
  const token = searchParams.get('invite');
  // Validated at render time (not in the effect) so no state is set synchronously
  // inside the effect body — a malformed link starts in the error state directly.
  const invalidLink = !leagueId || !token || platform !== 'ESPN';

  const [state, setState] = useState<JoinState>(
    invalidLink ? 'error' : 'joining',
  );
  const [error, setError] = useState<string | null>(
    invalidLink
      ? 'This invite link is invalid. Ask the league owner to share a fresh ' +
          'link with you.'
      : null,
  );
  const attempted = useRef(false);

  // Redeem once the user is signed in. The ref guards against a double-run (React
  // Strict Mode / re-renders) so the token is only submitted a single time.
  useEffect(() => {
    if (!isSignedIn || attempted.current || invalidLink) return;
    // Narrowed by `invalidLink`, but TS can't see it, so guard for the types.
    if (!leagueId || !token || platform !== 'ESPN') return;
    attempted.current = true;

    let cancelled = false;
    void (async () => {
      try {
        await acceptInvite(leagueId, platform, token);
        const league = await getLeague(leagueId, platform);
        if (cancelled) return;
        setLeagueCookies(leagueId, platform, league.data.seasons);
        void navigate('/home');
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError && (err.status === 403 || err.status === 404)
            ? 'This invite link is invalid or has been revoked. Ask the league ' +
                'owner for a new one.'
            : 'Something went wrong joining this league. Please try again.',
        );
        setState('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, leagueId, token, platform, invalidLink, navigate]);

  if (!isLoaded) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );
  }

  // Signed out: sign in, then Clerk returns to this exact invite URL to redeem.
  if (!isSignedIn) {
    const redirectUrl = `${location.pathname}${location.search}`;
    return (
      <Dialog open>
        <DialogContent
          className="p-0 overflow-hidden w-auto max-w-none bg-transparent border-none shadow-none ring-0"
          showCloseButton={false}
        >
          <DialogTitle className="sr-only">
            Sign in to join the league
          </DialogTitle>
          <SignIn
            routing="hash"
            forceRedirectUrl={redirectUrl}
            signUpForceRedirectUrl={redirectUrl}
          />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <Ticket className="size-6 text-muted-foreground" />
      </div>
      {state === 'joining' ? (
        <>
          <h1 className="text-2xl font-bold">Joining league…</h1>
          <Spinner className="size-6 text-muted-foreground" />
        </>
      ) : (
        <>
          <h1 className="text-2xl font-bold">Couldn&apos;t join this league</h1>
          {error && (
            <div className="w-full max-w-md">
              <ErrorAlert message={error} />
            </div>
          )}
          <Button
            className="cursor-pointer"
            onClick={() => void navigate('/connect_league')}
          >
            View another league
          </Button>
        </>
      )}
    </div>
  );
}
