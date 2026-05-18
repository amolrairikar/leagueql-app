import { BrowserAgent } from '@newrelic/browser-agent/loaders/browser-agent';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './index.css';

import ClerkWithTheme from './clerk-with-theme.tsx';

import { ThemeProvider } from '@/components/theme-provider';

if (import.meta.env.VITE_NEW_RELIC_LICENSE_KEY) {
  new BrowserAgent({
    init: {
      distributed_tracing: { enabled: true },
      privacy: { cookies_enabled: true },
    },
    info: {
      beacon: 'bam.nr-data.net',
      errorBeacon: 'bam.nr-data.net',
      licenseKey: import.meta.env.VITE_NEW_RELIC_LICENSE_KEY,
      applicationID: import.meta.env.VITE_NEW_RELIC_APPLICATION_ID,
      sa: 1,
    },
    loader_config: {
      accountID: import.meta.env.VITE_NEW_RELIC_ACCOUNT_ID,
      trustKey: import.meta.env.VITE_NEW_RELIC_TRUST_KEY,
      agentID: import.meta.env.VITE_NEW_RELIC_AGENT_ID,
      licenseKey: import.meta.env.VITE_NEW_RELIC_LICENSE_KEY,
      applicationID: import.meta.env.VITE_NEW_RELIC_APPLICATION_ID,
    },
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ClerkWithTheme />
    </ThemeProvider>
  </StrictMode>,
);
