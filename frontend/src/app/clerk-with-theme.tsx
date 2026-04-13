import { ClerkProvider } from '@clerk/react';
import { dark } from '@clerk/ui/themes';

import App from './app.tsx';

import { useTheme } from '@/hooks/use-theme';

export default function ClerkWithTheme() {
  const { theme } = useTheme();
  const isDark =
    theme === 'dark' ||
    (theme === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <ClerkProvider
      publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string}
      appearance={{ theme: isDark ? dark : undefined }}
    >
      <App />
    </ClerkProvider>
  );
}
