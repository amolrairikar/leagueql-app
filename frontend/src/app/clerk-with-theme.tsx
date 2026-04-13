import { ClerkProvider } from '@clerk/react';
import { dark } from '@clerk/ui/themes';

import App from './app.tsx';

import { useTheme } from '@/hooks/use-theme';

const CLERK_PUBLISHABLE_KEY =
  window.location.hostname === 'leagueql.com'
    ? 'pk_live_Y2xlcmsubGVhZ3VlcWwuY29tJA' // eslint-disable-line no-secrets/no-secrets -- Clerk publishable keys are intentionally public
    : 'pk_test_c2VsZWN0ZWQtZGluZ28tNTkuY2xlcmsuYWNjb3VudHMuZGV2JA'; // eslint-disable-line no-secrets/no-secrets -- Clerk publishable keys are intentionally public

export default function ClerkWithTheme() {
  const { theme } = useTheme();
  const isDark =
    theme === 'dark' ||
    (theme === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <ClerkProvider
      publishableKey={CLERK_PUBLISHABLE_KEY}
      appearance={{ theme: isDark ? dark : undefined }}
    >
      <App />
    </ClerkProvider>
  );
}
