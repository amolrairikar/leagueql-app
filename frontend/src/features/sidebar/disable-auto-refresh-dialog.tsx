import { useState } from 'react';

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
import { setAutoRefresh } from '@/features/connect_league/api-calls';
import { clearApiCache } from '@/lib/api-client';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Owner-side opt-out of scheduled auto-refresh for an ESPN league
 * (backend/scheduled-league-auto-refresh, frontend/navigation-sidebar). Calls
 * `PUT /leagues/{id}/auto-refresh` with `enabled=false`, which clears the enrollment
 * and — when this is the owner's last opted-in ESPN league — removes their stored ESPN
 * cookies. On success we clear the API cache and reload so `useIsOwner` re-reads
 * `auto_refresh_enabled`, restoring the manual Refresh League action.
 */
export function DisableAutoRefreshDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { leagueId, platform } = getLeagueCookies();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDisable() {
    setLoading(true);
    setError(null);
    try {
      await setAutoRefresh(leagueId, platform, false);
      // Drop the cached getLeague response so the reloaded app reflects the new
      // enrollment state (Refresh League action + reminder banner return).
      clearApiCache();
      window.location.reload();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to turn off automatic refresh.',
      );
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setError(null);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Turn off automatic refresh?</DialogTitle>
          <DialogDescription>
            This league will stop refreshing automatically each week. Your
            stored ESPN login will be removed, so you&apos;ll refresh manually
            from now on — to turn automatic refresh back on you&apos;ll re-enter
            your ESPN cookies on the refresh form.
          </DialogDescription>
        </DialogHeader>
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          <Button
            className="cursor-pointer"
            disabled={loading}
            onClick={() => void handleDisable()}
          >
            {loading && <Spinner className="size-4" />}
            Turn Off Auto-Refresh
          </Button>
          <Button
            variant="outline"
            className="cursor-pointer"
            disabled={loading}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
