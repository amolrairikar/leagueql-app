import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './index.css';

import ClerkWithTheme from './clerk-with-theme.tsx';

import { ThemeProvider } from '@/components/theme-provider';
import { initFeatureFlags } from '@/lib/feature-flags';
import { initTelemetry } from '@/lib/telemetry';

// OpenTelemetry tracing + Web Vitals → Axiom (FE-029). No-op unless VITE_TRACES_URL
// is configured (and never under Vitest), so dev/test bootstraps are unaffected.
initTelemetry();

function render() {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ThemeProvider>
        <ClerkWithTheme />
      </ThemeProvider>
    </StrictMode>,
  );
}

// Resolve global feature flags from the backend (AWS AppConfig, FE-026) before
// first paint so the UI renders with the right flags, then render regardless of
// the outcome (a failed fetch leaves the fail-safe all-off flags). No-op under
// Vitest, where initFeatureFlags resolves immediately.
void initFeatureFlags().finally(render);
