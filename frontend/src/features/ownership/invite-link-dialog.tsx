import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

import { createInviteToken } from '@/components/api/leagues';
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
 * Owner-side ESPN invite link (backend/league-authorization / frontend/ownership-transfer).
 * Mints a reusable invite token and composes the shareable link the owner hands to
 * their leaguemates; anyone who opens it and signs in is added to the league's
 * members without ESPN cookies. Creating a new link revokes the previous one. The
 * plaintext token is shown once; only its hash is stored server-side.
 */
export function InviteLinkDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { leagueId, platform } = getLeagueCookies();
  const [loading, setLoading] = useState(false);
  const [generated, setGenerated] = useState<{
    leagueId: string;
    url: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [justGenerated, setJustGenerated] = useState(false);

  // The plaintext link is only returned once (the server keeps just its hash), so
  // it is remembered in memory and re-shown when the dialog is reopened rather
  // than forcing a regenerate. The sidebar dialog stays mounted across league
  // switches, so it is scoped to the league it was minted for — a link for a
  // previously viewed league must never leak into another league's dialog.
  const link = generated?.leagueId === leagueId ? generated.url : null;

  // Cleared on close; the remembered link is intentionally kept.
  function clearTransient() {
    setError(null);
    setCopied(false);
    setJustGenerated(false);
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
    setCopied(false);
    setJustGenerated(false);
    try {
      const res = await createInviteToken(leagueId, platform);
      const params = new URLSearchParams({ platform, invite: res.data.token });
      setGenerated({
        leagueId,
        url: `${window.location.origin}/join/${leagueId}?${params}`,
      });
      setJustGenerated(true);
      setTimeout(() => setJustGenerated(false), 3000);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create invite link.',
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
        if (!next) clearTransient();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite leaguemates</DialogTitle>
          <DialogDescription>
            Create a link and share it with your leaguemates. Anyone who opens
            it and signs into LeagueQL can view this league — no ESPN cookies
            needed. Creating a new link revokes the previous one.
          </DialogDescription>
        </DialogHeader>
        {link ? (
          <div className="flex items-center gap-2">
            <Input readOnly value={link} aria-label="Invite link" />
            <Button
              variant="outline"
              className="cursor-pointer"
              onClick={() => handleCopy(link)}
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
        {justGenerated && (
          <p
            role="status"
            className="flex items-center gap-1.5 text-sm font-medium text-green-600 dark:text-green-400"
          >
            <Check className="size-4 shrink-0" />
            New link created. Copy it and share it with your leaguemates.
          </p>
        )}
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          <Button
            className="cursor-pointer"
            disabled={loading}
            onClick={() => void handleGenerate()}
          >
            {loading && <Spinner className="size-4" />}
            {link ? 'Create new link' : 'Create invite link'}
          </Button>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => {
              clearTransient();
              onOpenChange(false);
            }}
          >
            {link ? 'Done' : 'Cancel'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
