import { Megaphone, X } from 'lucide-react';
import { useState } from 'react';

import { isDemoMode } from '@/lib/cookie-handler';
import { isBannerEnabled } from '@/lib/feature-flags';

// Current banner content. This is the one place to edit for any banner update —
// swap the message/link to promote whatever the active campaign is (Discord
// today). The banner only shows once the `banner` feature flag (frontend/informational-banner) is on.
// The message is rendered as PREFIX + LINK_LABEL + SUFFIX, with LINK_LABEL turned
// into the link when LINK_URL is set — so the link lives inline within the
// sentence (today: the word "community" links to the Discord invite). Leave
// LINK_URL empty for a link-less, message-only banner.
const BANNER_MESSAGE_PREFIX = 'Join the LeagueQL Discord ';
const BANNER_LINK_LABEL = 'community';
const BANNER_MESSAGE_SUFFIX = '!';
const BANNER_LINK_URL = 'https://discord.gg/jE2dm89GWh';

// localStorage key remembering a dismissal so the banner stays hidden for this
// browser (frontend/informational-banner). Mirrors the direct localStorage pattern in theme-provider.tsx.
const DISMISSED_STORAGE_KEY = 'leagueql.bannerDismissed';

// localStorage can throw (private browsing, disabled storage, or an unwired test
// env), so read/write defensively — a storage failure must never crash the app or
// the banner. A failed read just treats the banner as not-yet-dismissed.
function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function persistDismissed(): void {
  try {
    localStorage.setItem(DISMISSED_STORAGE_KEY, 'true');
  } catch {
    // Non-fatal: the banner still hides for this session via component state.
  }
}

/**
 * Thin, full-width informational banner below the in-app header (frontend/informational-banner). A
 * generic, content-driven banner (see the BANNER_* constants) gated behind the
 * `banner` feature flag and dismissible — a dismissal is remembered in
 * localStorage. Renders nothing when the flag is off, in demo mode, or once the
 * user has dismissed it.
 */
export function Banner() {
  const [dismissed, setDismissed] = useState(readDismissed);

  // Suppressed in demo mode so the promotional invite doesn't clutter the
  // sample-data experience (frontend/informational-banner).
  if (!isBannerEnabled() || isDemoMode() || dismissed) return null;

  const dismiss = () => {
    persistDismissed();
    setDismissed(true);
  };

  return (
    <div className="relative flex h-8 shrink-0 items-center justify-center gap-2 border-b border-primary/50 bg-primary/40 px-4">
      <Megaphone className="size-3.5 text-white" aria-hidden="true" />
      <span className="text-[0.72rem] font-medium tracking-wide text-white">
        {BANNER_MESSAGE_PREFIX}
        {BANNER_LINK_URL ? (
          <a
            href={BANNER_LINK_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:no-underline"
          >
            {BANNER_LINK_LABEL}
          </a>
        ) : (
          BANNER_LINK_LABEL
        )}
        {BANNER_MESSAGE_SUFFIX}
      </span>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss banner"
        className="absolute right-4 cursor-pointer text-white/80 hover:text-white"
      >
        <X className="size-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}
