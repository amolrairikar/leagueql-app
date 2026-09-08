import { defineManifest } from '@crxjs/vite-plugin';

import pkg from './package.json';

const icons = {
  '16': 'icons/icon-16.png',
  '48': 'icons/icon-48.png',
  '128': 'icons/icon-128.png',
};

// Loopback origins are DEV-ONLY. A page served from the user's localhost is not a
// trust boundary — the content script's only gate on releasing ESPN cookies is that
// the page origin is in `matches`, so shipping loopback in the published extension
// would let any local page harvest the user's ESPN session cookies (SEC-03 /
// extension/espn-cookie-autofill). They are added only in non-production builds and
// scoped to the Vite dev server port so local development still works.
const DEV_LOOPBACK_MATCHES = [
  'http://localhost:5173/*',
  'http://127.0.0.1:5173/*',
];

export default defineManifest((env) => ({
  manifest_version: 3,
  name: 'LeagueQL ESPN Cookie Helper',
  version: pkg.version,
  description: pkg.description,
  icons,
  action: {
    default_icon: icons,
    default_title: 'LeagueQL ESPN Cookie Helper',
    default_popup: 'src/popup.html',
  },
  // `cookies` lets the service worker read ESPN's auth cookies; the host
  // permission scopes that access to ESPN only.
  permissions: ['cookies'],
  host_permissions: ['https://*.espn.com/*'],
  background: {
    service_worker: 'src/background.ts',
    type: 'module',
  },
  // The content-script bridge is injected only on LeagueQL origins, so ESPN
  // cookies can only ever be relayed to a LeagueQL page. Loopback dev origins are
  // added only in non-production builds (see DEV_LOOPBACK_MATCHES above).
  content_scripts: [
    {
      matches: [
        'https://leagueql.com/*',
        'https://*.leagueql.com/*',
        ...(env.mode === 'production' ? [] : DEV_LOOPBACK_MATCHES),
      ],
      js: ['src/content.ts'],
      run_at: 'document_idle',
    },
  ],
}));
