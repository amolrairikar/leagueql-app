import { RUNTIME_MSG, WINDOW_MSG, type EspnCookieResult } from './messages';

const ORIGIN = window.location.origin;

// Announce availability so the page can show the "Autofill from ESPN" button.
// The page reads this attribute on mount and also listens for the ready message
// in case the content script loads after the page has rendered.
document.documentElement.setAttribute('data-leagueql-espn-extension', '1');
window.postMessage({ type: WINDOW_MSG.ready }, ORIGIN);

window.addEventListener('message', (event: MessageEvent) => {
  // Only trust same-window requests of the expected type.
  if (event.source !== window) return;
  const data = event.data as { type?: string } | null;
  if (!data || data.type !== WINDOW_MSG.request) return;

  chrome.runtime.sendMessage(
    { type: RUNTIME_MSG.getEspnCookies },
    (result: EspnCookieResult | undefined) => {
      const payload: EspnCookieResult =
        chrome.runtime.lastError || !result
          ? { ok: false, error: 'not_logged_in' }
          : result;
      window.postMessage({ type: WINDOW_MSG.response, ...payload }, ORIGIN);
    },
  );
});
