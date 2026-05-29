# LeagueQL ESPN Cookie Helper

A Manifest V3 Chrome extension that reads your ESPN `SWID` and `espn_s2`
cookies and auto-fills them into the LeagueQL onboarding / refresh form, so you
don't have to copy them out of DevTools by hand.

## How it works

A web page on `leagueql.com` cannot read `.espn.com` cookies (cross-origin), so
the extension does it:

```
leagueql.com page  ──window.postMessage──▶  content script  ──chrome.runtime──▶  service worker
   (autofill)       ◀──window.postMessage──   (bridge)        ◀──chrome.runtime──   (chrome.cookies.get on .espn.com)
```

- **`src/background.ts`** — service worker; reads the ESPN cookies via
  `chrome.cookies.get`.
- **`src/content.ts`** — injected only on LeagueQL origins; bridges the page's
  `window.postMessage` requests to the service worker. It also flags the page
  (`<html data-leagueql-espn-extension="1">`) so the form knows the extension is
  installed.
- **`src/messages.ts`** — the shared message protocol. The page-side mirror is
  `frontend/src/lib/espn-extension.ts`; keep the string values in sync.

The extension never stores credentials and only relays them to LeagueQL pages.

## Develop / build

```bash
npm install
npm run dev      # Vite dev server with HMR (writes to dist/)
npm run build    # type-check + production build to dist/
```

## Load unpacked (for testing)

1. `npm run build` (or `npm run dev`).
2. Open `chrome://extensions`.
3. Enable **Developer mode** (top-right).
4. **Load unpacked** → select this directory's `dist/` folder.
5. Log in at `fantasy.espn.com`, open the LeagueQL onboard form, pick **ESPN**,
   and click **Autofill from ESPN**.

## Publishing to the Chrome Web Store

`npm run build`, then zip the contents of `dist/` and upload the zip in the
Chrome Web Store Developer Dashboard.
