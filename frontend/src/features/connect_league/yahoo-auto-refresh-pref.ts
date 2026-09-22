// The Yahoo auto-refresh opt-in is chosen before the OAuth redirect but applied when the
// return leg auto-onboards, so it must survive a full-page navigation. Stash it in
// sessionStorage (scoped to the tab, cleared once consumed). All access is wrapped so a
// private-mode / storage-blocked browser degrades to "not opted in" rather than throwing.
const KEY = 'leagueql:yahoo-auto-refresh';

export function setYahooAutoRefreshPref(enabled: boolean): void {
  try {
    if (enabled) sessionStorage.setItem(KEY, '1');
    else sessionStorage.removeItem(KEY);
  } catch {
    // Storage unavailable — the choice simply won't carry across the redirect (defaults off).
  }
}

/** Read and clear the stored Yahoo opt-in choice (single-use across the OAuth redirect). */
export function takeYahooAutoRefreshPref(): boolean {
  try {
    const v = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return v === '1';
  } catch {
    return false;
  }
}
