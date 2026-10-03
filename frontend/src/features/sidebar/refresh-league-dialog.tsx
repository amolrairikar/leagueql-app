import { HelpCircle } from 'lucide-react';
import { useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  type OnboardRequest,
  onboardLeague,
} from '@/features/connect_league/api-calls';
import { EspnCredentialFields } from '@/features/connect_league/espn-credential-fields';
import { pollForCompletion, sleep } from '@/features/connect_league/poll';
import { ApiError, clearApiCache } from '@/lib/api-client';
import {
  clearEspnCookies,
  getLeagueCookies,
  setLeagueCookies,
} from '@/lib/cookie-handler';
import { getCurrentNflSeason } from '@/lib/season';

const MAX_REFRESH_ATTEMPTS = 3;
const REFRESH_RETRY_DELAY_MS = 2000;
const POLL_INITIAL_DELAY_MS = 5000;

/**
 * In-dashboard manual refresh for an ESPN league (frontend/navigation-sidebar,
 * frontend/connect-league). Replaces the trip to the `/connect_league` form: the
 * owner enters their SWID/espn_s2 (via the extension or manually, using the same
 * tooltips) and the league refreshes in place. The season is derived
 * automatically (Sleeper NFL state, clock fallback), never entered.
 *
 * ESPN cookies are transmitted once over HTTPS and cleared from the browser on
 * success; the manual-refresh action only appears for a league not enrolled in
 * auto-refresh, so the opt-in defaults off. An opted-in refresh that is blocked
 * (`429` cooldown / `409` up to date or in progress) still enrolls the league
 * server-side (backend/league-refresh), so the dialog confirms auto-refresh is on
 * and reloads into the enrolled state when closed.
 *
 * In `reauth` mode (an auto-refreshed league whose stored cookies ESPN rejected,
 * `espn_reauth_required`) the dialog is titled "Update ESPN Cookies" and the
 * opt-in starts checked, so submitting re-stores the cookies — via a successful
 * refresh or the blocked-refresh enrollment — which clears the rejection and
 * resumes automatic refresh (backend/espn-credential-storage).
 */
export function RefreshLeagueDialog({
  open,
  onOpenChange,
  reauth = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reauth?: boolean;
}) {
  const { leagueId } = getLeagueCookies();
  const [swid, setSwid] = useState('');
  const [espnS2, setEspnS2] = useState('');
  // Opt into scheduled auto-refresh. Defaults off: the manual action only appears
  // for a league not already enrolled (backend/scheduled-league-auto-refresh). In
  // reauth mode the league is already enrolled, so keep it opted in.
  const [autoRefresh, setAutoRefresh] = useState(reauth);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cooldownNotice, setCooldownNotice] = useState<string | null>(null);
  // Set when an opted-in refresh was blocked but the league was still enrolled.
  const [enrolled, setEnrolled] = useState(false);

  function reset() {
    setError(null);
    setCooldownNotice(null);
    setLoadingMessage('');
  }

  async function handleRefresh() {
    if (!swid.trim() || !espnS2.trim()) {
      setError('Enter your SWID and espn_s2 to refresh a private ESPN league.');
      return;
    }
    reset();
    setLoading(true);
    setLoadingMessage("Fetching your league's data");

    const body: OnboardRequest = {
      leagueId,
      platform: 'ESPN',
      // Derived automatically (Sleeper NFL state, clock fallback), never entered.
      season: await getCurrentNflSeason(),
      s2: espnS2.trim(),
      swid: swid.trim(),
      // When checked, the league enrolls in scheduled weekly auto-refresh and the
      // backend stores the ESPN cookies encrypted for reuse.
      autoRefresh,
    };

    let correlationId: string | null = null;
    let capturedError: ApiError | null = null;
    for (let attempt = 1; attempt <= MAX_REFRESH_ATTEMPTS; attempt++) {
      try {
        const res = await onboardLeague('REFRESH', body);
        correlationId = res.data.correlation_id;
        clearEspnCookies();
        break;
      } catch (err) {
        capturedError = err instanceof ApiError ? err : null;
        const status = capturedError?.status ?? 0;
        const isRetryable = status === 0 || status >= 500;
        if (!isRetryable || attempt === MAX_REFRESH_ATTEMPTS) break;
        await sleep(REFRESH_RETRY_DELAY_MS);
      }
    }

    if (!correlationId) {
      // A 429 weekly cooldown or a 409 already-up-to-date / in-progress response is
      // a benign state, not a failure — surface the backend message neutrally.
      if (
        capturedError &&
        (capturedError.status === 429 || capturedError.status === 409)
      ) {
        setCooldownNotice(capturedError.message);
        if (autoRefresh) {
          // The backend validated + stored the cookies and enrolled the league
          // before returning the block, so they're no longer needed here.
          setEnrolled(true);
          clearEspnCookies();
        }
      } else if (capturedError?.status === 400) {
        // An opted-in blocked refresh whose cookies ESPN rejected: the backend
        // message tells the owner to re-enter them.
        setError(capturedError.message);
      } else {
        setError('League refresh failed. Please try again.');
      }
      setLoading(false);
      return;
    }

    setLoadingMessage('Calculating');
    await sleep(POLL_INITIAL_DELAY_MS);
    const result = await pollForCompletion(correlationId);
    if (result.status === 'failed') {
      setError(
        result.failureReason ?? 'League refresh failed. Please try again.',
      );
      setLoading(false);
      return;
    }

    // Refresh wrote new precomputed views (and possibly new seasons); drop cached
    // reads, refresh the stored season list, then reload so the dashboard shows the
    // fresh data in place.
    setLoadingMessage('Updating your league dashboard');
    clearApiCache();
    try {
      const league = await getLeague(leagueId, 'ESPN');
      setLeagueCookies(leagueId, 'ESPN', league.data.seasons);
    } catch {
      // A failed re-read just means the reload re-fetches; keep going.
    }
    window.location.reload();
  }

  function handleOpenChange(next: boolean) {
    // Ignore close attempts mid-refresh so the in-flight job isn't abandoned.
    if (loading) return;
    if (!next && enrolled) {
      // Reload so the sidebar re-reads auto_refresh_enabled and swaps Refresh
      // League for Turn Off Auto-Refresh.
      clearApiCache();
      window.location.reload();
      return;
    }
    onOpenChange(next);
    if (!next) {
      reset();
      setSwid('');
      setEspnS2('');
      setAutoRefresh(reauth);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-center">
            {reauth ? 'Update ESPN Cookies' : 'Refresh League'}
          </DialogTitle>
          <DialogDescription>
            {reauth
              ? 'ESPN rejected your saved cookies, so automatic refresh is paused. Enter your current ESPN cookies to resume it.'
              : "Enter your ESPN cookies to pull your league's latest data."}{' '}
            Your cookies are sent once and cleared from your browser afterward.
          </DialogDescription>
        </DialogHeader>
        <EspnCredentialFields
          swid={swid}
          espnS2={espnS2}
          onSwidChange={setSwid}
          onEspnS2Change={setEspnS2}
          onAutofill={(nextSwid, nextEspnS2) => {
            setSwid(nextSwid);
            setEspnS2(nextEspnS2);
          }}
          disabled={loading || enrolled}
          showManualInstructions={false}
        />
        <div className="flex items-center gap-2">
          <input
            id="refresh-auto-refresh"
            type="checkbox"
            className="size-4 cursor-pointer accent-primary"
            checked={autoRefresh}
            disabled={loading || enrolled}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <div className="flex items-center gap-1.5">
            <Label htmlFor="refresh-auto-refresh" className="cursor-pointer">
              Enable automatic weekly refresh
            </Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="right" className="max-w-64">
                  When enabled, LeagueQL securely stores your ESPN cookies
                  (encrypted) and refreshes your league automatically each week
                  during the season. ESPN cookies expire periodically, so you
                  may occasionally need to re-enter them.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
        {cooldownNotice && enrolled && (
          <Alert>
            <AlertTitle>Automatic refresh enabled</AlertTitle>
            <AlertDescription>
              This league will now refresh automatically each week. It
              wasn&apos;t refreshed just now: {cooldownNotice}
            </AlertDescription>
          </Alert>
        )}
        {cooldownNotice && !enrolled && (
          <Alert>
            <AlertTitle>Refresh not available yet</AlertTitle>
            <AlertDescription>{cooldownNotice}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Refresh Failed</AlertTitle>
            <AlertDescription>
              {error} If the error persists, contact{' '}
              <a
                href="mailto:support@leagueql.com"
                className="underline underline-offset-4"
              >
                support
              </a>
              .
            </AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          {enrolled ? (
            <Button
              className="cursor-pointer"
              onClick={() => handleOpenChange(false)}
            >
              Done
            </Button>
          ) : (
            <>
              <Button
                className="cursor-pointer"
                disabled={loading}
                onClick={() => void handleRefresh()}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Spinner className="size-4" />
                    {loadingMessage}
                  </span>
                ) : (
                  'Refresh League'
                )}
              </Button>
              <Button
                variant="outline"
                className="cursor-pointer"
                disabled={loading}
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
