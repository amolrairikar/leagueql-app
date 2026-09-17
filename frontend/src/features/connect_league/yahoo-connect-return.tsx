import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  getYahooAuthorizeUrl,
  onboardYahooLeague,
} from '@/features/connect_league/api-calls';
import { pollForCompletion } from '@/features/connect_league/poll';
import { ApiError, clearApiCache } from '@/lib/api-client';
import { isDemoMode, setLeagueCookies } from '@/lib/cookie-handler';

// The backend re-link signal (backend/yahoo-oauth): a job that fails because the owner's
// Yahoo token was revoked mid-onboard carries this code so we prompt a reconnect.
const YAHOO_AUTH_CODE = 'YAHOO_AUTH';

type YahooState =
  | 'linking' // resolving the onboard + polling after a successful link
  | 'reconnect' // the link was lost/expired — restart OAuth
  | 'declined' // the user cancelled or the link failed
  | 'error'; // an unexpected failure

/**
 * Renders the return leg of the Yahoo OAuth flow (frontend/connect-yahoo-league).
 *
 * Yahoo redirects the browser back to the `/connect_league` page with a platform=YAHOO
 * query param and a yahooLinked flag (1 on success, 0 on decline/failure).
 * On a successful link this resumes onboarding for the carried league id and polls the job to
 * completion (the same flow as ESPN/Sleeper), navigating home on success; a declined link, a
 * lost link, or a `YAHOO_AUTH` job failure shows a retry / reconnect prompt. No Yahoo tokens
 * ever touch the browser.
 */
export default function YahooConnectReturn({
  linked,
  leagueId,
}: {
  linked: boolean;
  leagueId: string;
}) {
  const navigate = useNavigate();
  const [state, setState] = useState<YahooState>(
    linked ? 'linking' : 'declined',
  );
  const [reconnecting, setReconnecting] = useState(false);
  // Guard against the effect resuming onboarding twice (e.g. React StrictMode).
  const startedRef = useRef(false);

  useEffect(() => {
    if (!linked || startedRef.current) return;
    startedRef.current = true;
    void (async () => {
      try {
        const result = await onboardYahooLeague(leagueId);
        const pollResult = await pollForCompletion(result.data.correlation_id);
        if (pollResult.status === 'failed') {
          // A revoked/expired Yahoo token surfaces as a FAILED job with YAHOO_AUTH —
          // prompt a reconnect rather than a generic failure (backend/yahoo-oauth).
          setState(
            pollResult.failureCode === YAHOO_AUTH_CODE ? 'reconnect' : 'error',
          );
          return;
        }
        // Onboarding wrote new precomputed views; drop cached reads before re-reading.
        clearApiCache();
        const leagueData = await getLeague(leagueId, 'YAHOO');
        setLeagueCookies(leagueId, 'YAHOO', leagueData.data.seasons);
        void navigate('/home');
      } catch (err) {
        // 403 at submit means the backend has no valid link for this caller
        // (revoked/expired) — prompt a reconnect (backend/yahoo-oauth).
        setState(
          err instanceof ApiError && err.status === 403 ? 'reconnect' : 'error',
        );
      }
    })();
  }, [linked, leagueId, navigate]);

  const restartOauth = async () => {
    // Demo mode never links a real account (frontend/demo-mode); bounce home instead.
    if (isDemoMode()) {
      void navigate('/home');
      return;
    }
    // A declined link lost the league id (the callback carries none), so send the user
    // back to the connect form to re-enter it; a reconnect still has the league id.
    if (!leagueId) {
      void navigate('/');
      return;
    }
    setReconnecting(true);
    try {
      const { data } = await getYahooAuthorizeUrl(leagueId);
      window.location.href = data.authorize_url;
    } catch {
      setReconnecting(false);
      setState('error');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden">
      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center font-bold">
              Connect Yahoo League
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {state === 'linking' && (
              <div className="flex items-center justify-center gap-2 py-4 text-muted-foreground">
                <Spinner />
                Onboarding your Yahoo league — this can take a moment
              </div>
            )}

            {state === 'declined' && (
              <Alert variant="destructive">
                <AlertTitle>Yahoo connection cancelled</AlertTitle>
                <AlertDescription>
                  Yahoo linking was cancelled or failed — try again.
                </AlertDescription>
              </Alert>
            )}

            {state === 'reconnect' && (
              <Alert variant="destructive">
                <AlertTitle>Reconnect your Yahoo account</AlertTitle>
                <AlertDescription>
                  Your Yahoo connection expired. Reconnect your account to
                  continue.
                </AlertDescription>
              </Alert>
            )}

            {state === 'error' && (
              <Alert variant="destructive">
                <AlertTitle>Something went wrong</AlertTitle>
                <AlertDescription>
                  We couldn&apos;t complete your Yahoo connection. Please try
                  again.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1 cursor-pointer"
                onClick={() => void navigate('/')}
              >
                Back
              </Button>
              {(state === 'declined' ||
                state === 'reconnect' ||
                state === 'error') && (
                <Button
                  type="button"
                  className="flex-1 cursor-pointer"
                  disabled={reconnecting}
                  onClick={() => void restartOauth()}
                >
                  {reconnecting ? (
                    <span className="flex items-center gap-2">
                      <Spinner className="text-primary-foreground" />
                      Reconnecting
                    </span>
                  ) : (
                    'Connect with Yahoo'
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
