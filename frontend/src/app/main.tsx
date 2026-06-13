import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './index.css';

import ClerkWithTheme from './clerk-with-theme.tsx';

import { ThemeProvider } from '@/components/theme-provider';
import { initTelemetry } from '@/lib/telemetry';

// OpenTelemetry tracing + Web Vitals → Axiom (FE-029). No-op unless VITE_TRACES_URL
// is configured (and never under Vitest), so dev/test bootstraps are unaffected.
initTelemetry();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ClerkWithTheme />
    </ThemeProvider>
  </StrictMode>,
);
