import { RUNTIME_MSG, type EspnCookieResult } from './messages';

// Any ESPN URL works for cookie lookup; both cookies are scoped to .espn.com.
const ESPN_URL = 'https://fantasy.espn.com';

async function readEspnCookies(): Promise<EspnCookieResult> {
  const [swidCookie, s2Cookie] = await Promise.all([
    chrome.cookies.get({ url: ESPN_URL, name: 'SWID' }),
    chrome.cookies.get({ url: ESPN_URL, name: 'espn_s2' }),
  ]);
  // SWID is returned raw, including its surrounding curly braces.
  const swid = swidCookie?.value ?? '';
  const espnS2 = s2Cookie?.value ?? '';
  if (!swid || !espnS2) {
    return { ok: false, error: 'not_logged_in' };
  }
  return { ok: true, swid, espnS2 };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== RUNTIME_MSG.getEspnCookies) {
    return undefined;
  }
  readEspnCookies()
    .then(sendResponse)
    .catch(() => {
      sendResponse({ ok: false, error: 'not_logged_in' } satisfies EspnCookieResult);
    });
  // Keep the message channel open for the async response.
  return true;
});
