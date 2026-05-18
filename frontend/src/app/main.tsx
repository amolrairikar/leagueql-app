import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './index.css';

import ClerkWithTheme from './clerk-with-theme.tsx';

import { ThemeProvider } from '@/components/theme-provider';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ClerkWithTheme />
    </ThemeProvider>
  </StrictMode>,
);
