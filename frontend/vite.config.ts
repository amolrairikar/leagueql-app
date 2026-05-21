import path from 'path';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import svgr from 'vite-plugin-svgr';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react(), tailwindcss(), svgr()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    // Scope to src/ only — the e2e/ directory contains Playwright tests, not Vitest tests.
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    // Satisfies getBaseUrl() at module import time without hitting PROD or dev-URL paths.
    env: {
      VITE_API_URL: 'http://test.local',
    },
  },
});
