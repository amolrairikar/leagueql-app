import { useSyncExternalStore } from 'react';

import {
  isEspnExtensionAvailable,
  onEspnExtensionReady,
} from '@/lib/espn-extension';

/**
 * Whether the LeagueQL ESPN Cookie Helper extension's content script has flagged
 * this page. Re-renders when the extension announces readiness after mount (its
 * content script can load late), and reads the current state synchronously during
 * render via `useSyncExternalStore` — no mount flash, no self-disabling effect.
 */
export function useEspnExtensionReady(): boolean {
  return useSyncExternalStore(onEspnExtensionReady, isEspnExtensionAvailable);
}
