import { defineManifest } from '@crxjs/vite-plugin';

import pkg from './package.json';

const icons = {
  '16': 'icons/icon-16.png',
  '48': 'icons/icon-48.png',
  '128': 'icons/icon-128.png',
};

export default defineManifest({
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
  // cookies can only ever be relayed to a LeagueQL page.
  content_scripts: [
    {
      matches: [
        'https://leagueql.com/*',
        'https://*.leagueql.com/*',
        'http://localhost/*',
        'http://127.0.0.1/*',
      ],
      js: ['src/content.ts'],
      run_at: 'document_idle',
    },
  ],
});
