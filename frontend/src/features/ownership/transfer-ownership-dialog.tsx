import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

import { createTransferToken } from '@/components/api/leagues';
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
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Owner-side ownership transfer (backend/league-authorization / frontend/ownership-transfer). Mints a one-time token the
 * owner hands to the recipient, who redeems it via the claim flow. The plaintext
 * token is shown once; only its hash is stored server-side.
 */
export function TransferOwnershipDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { leagueId, platform } = getLeagueCookies();
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  function reset() {
    setToken(null);
    setError(null);
    setCopied(false);
  }

  function handleCopy(value: string) {
    void navigator.clipboard?.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await createTransferToken(leagueId, platform);
      setToken(res.data.token);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create transfer token.',
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
          <DialogTitle>Transfer ownership</DialogTitle>
          <DialogDescription>
            Generate a one-time token and share it with the new owner. They
            redeem it from their account to take over this league. The token
            expires in 24 hours.
          </DialogDescription>
        </DialogHeader>
        {token ? (
          <div className="flex items-center gap-2">
            <Input readOnly value={token} aria-label="Transfer token" />
            <Button
              variant="outline"
              className="cursor-pointer"
              onClick={() => handleCopy(token)}
            >
              {copied ? (
                <>
                  <Check className="size-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="size-4" />
                  Copy
                </>
              )}
            </Button>
          </div>
        ) : null}
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          {!token && (
            <Button
              className="cursor-pointer"
              disabled={loading}
              onClick={() => void handleGenerate()}
            >
              {loading && <Spinner className="size-4" />}
              Generate token
            </Button>
          )}
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            {token ? 'Done' : 'Cancel'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
