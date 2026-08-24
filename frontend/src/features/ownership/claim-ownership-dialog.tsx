import { useState } from 'react';

import { claimOwnership } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
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
import { clearApiCache } from '@/lib/api-client';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Recipient-side ownership claim (backend/league-authorization / frontend/ownership-transfer). Redeems a transfer token the
 * current owner generated; on success the caller becomes the owner.
 */
export function ClaimOwnershipDialog({
  open,
  onOpenChange,
  onClaimed,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClaimed?: () => void;
}) {
  const { leagueId, platform } = getLeagueCookies();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClaim() {
    setLoading(true);
    setError(null);
    try {
      await claimOwnership(leagueId, platform as Platform, token.trim());
      clearApiCache();
      onOpenChange(false);
      if (onClaimed) onClaimed();
      else window.location.reload();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to claim ownership.',
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
        if (!next) {
          setToken('');
          setError(null);
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Claim ownership</DialogTitle>
          <DialogDescription>
            Paste the transfer token the current owner gave you to take over
            this league.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2">
          <Label htmlFor="transfer-token">Transfer token</Label>
          <Input
            id="transfer-token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          <Button
            className="cursor-pointer"
            disabled={loading || !token.trim()}
            onClick={() => void handleClaim()}
          >
            {loading && <Spinner className="size-4" />}
            Claim ownership
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
