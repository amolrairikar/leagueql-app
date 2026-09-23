import { useState } from 'react';

/**
 * Copy-to-clipboard with a transient `copied` flag that auto-clears.
 *
 * `copy(value)` writes to the clipboard and, on success, flips `copied` to true
 * for `resetMs` before clearing it (drives the "Copied!" affordance). Guards on
 * the optional `navigator.clipboard` so it no-ops in environments without it.
 * `resetCopied()` lets a dialog clear the flag when it closes/resets.
 */
export function useCopyToClipboard(resetMs = 2000): {
  copied: boolean;
  copy: (value: string) => void;
  resetCopied: () => void;
} {
  const [copied, setCopied] = useState(false);

  const copy = (value: string) => {
    void navigator.clipboard?.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    });
  };

  const resetCopied = () => setCopied(false);

  return { copied, copy, resetCopied };
}
