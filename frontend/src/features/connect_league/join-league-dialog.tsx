import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague, verifyMembership } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useEspnExtensionReady } from '@/hooks/use-espn-extension-ready';
import { ApiError } from '@/lib/api-client';
import { setLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import {
  ESPN_EXTENSION_URL,
  EspnExtensionError,
  requestEspnCookies,
} from '@/lib/espn-extension';

/**
 * "Join League" flow for an already-onboarded **private ESPN league** the caller
 * isn't a member of yet (LQL-01 / BE-016 / FE-002 / FE-025). It is distinct from
 * the onboard/refresh form: it only verifies membership (no onboard/refresh
 * request). The caller supplies their ESPN cookies (extension autofill or manual
 * entry); on success they're added to the league's members, the league cookies
 * are set, and they're routed to the dashboard.
 */
export function JoinLeagueDialog({
  open,
  onOpenChange,
  leagueId,
  onJoined,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leagueId: string;
  /**
   * Called after a successful verify instead of the default "set league cookies +
   * navigate home" behavior. Used by the in-app `MembershipGuard`, where the
   * league cookies are already set and the current page just needs to re-render.
   */
  onJoined?: () => void;
}) {
  const navigate = useNavigate();
  const [swid, setSwid] = useState('');
  const [s2, setS2] = useState('');
  const [loading, setLoading] = useState(false);
  const [autofilling, setAutofilling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const extensionReady = useEspnExtensionReady();

  function reset() {
    setSwid('');
    setS2('');
    setError(null);
  }

  async function handleAutofill() {
    setError(null);
    setAutofilling(true);
    try {
      const cookies = await requestEspnCookies();
      setSwid(cookies.swid);
      setS2(cookies.espnS2);
    } catch (err) {
      setError(
        err instanceof EspnExtensionError && err.reason === 'not_logged_in'
          ? 'Log into ESPN in your browser, then try again.'
          : 'Could not reach the ESPN extension. Enter your cookies manually instead.',
      );
    } finally {
      setAutofilling(false);
    }
  }

  async function handleJoin() {
    setLoading(true);
    setError(null);
    try {
      await verifyMembership(leagueId, 'ESPN', { swid, s2 });
      onOpenChange(false);
      if (onJoined) {
        // Caller (e.g. the in-app guard) handles what happens next — the league
        // cookies are already set and only a re-render/refetch is needed.
        onJoined();
        return;
      }
      // Default: membership confirmed — read the league (now 200) for its seasons
      // and open it.
      const league = await getLeague(leagueId, 'ESPN');
      setLeagueCookies(leagueId, 'ESPN', league.data.seasons);
      void navigate('/home');
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "We couldn't confirm you're in this ESPN league."
          : err instanceof Error
            ? err.message
            : 'Failed to join league.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) reset();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Join league</DialogTitle>
          <DialogDescription>
            This ESPN league is private. Verify your ESPN membership to join it
            and view its dashboard.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="grid gap-2">
            <Label htmlFor="join-swid">SWID</Label>
            <Input
              id="join-swid"
              value={swid}
              onChange={(e) => setSwid(e.target.value)}
              placeholder="Enter your SWID"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="join-espn-s2">ESPN S2</Label>
            <Input
              id="join-espn-s2"
              value={s2}
              onChange={(e) => setS2(e.target.value)}
              placeholder="Enter your ESPN S2 token"
            />
          </div>
          {extensionReady ? (
            <Button
              type="button"
              variant="outline"
              className="cursor-pointer"
              disabled={autofilling}
              onClick={() => void handleAutofill()}
            >
              {autofilling && <Spinner className="size-4" />}
              Autofill cookies from ESPN
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">
              Tired of copying cookies?{' '}
              <a
                href={ESPN_EXTENSION_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-4"
              >
                Get the LeagueQL ESPN Cookie Helper extension
              </a>{' '}
              to autofill them automatically.
            </p>
          )}
        </div>
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          <Button
            className="cursor-pointer"
            disabled={loading || !swid.trim() || !s2.trim()}
            onClick={() => void handleJoin()}
          >
            {loading && <Spinner className="size-4" />}
            Join league
          </Button>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
