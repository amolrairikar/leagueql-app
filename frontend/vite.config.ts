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
    // jest-cucumber's defineFeature/test run against Vitest's global describe/it.
    globals: true,
    // Shared component-test setup: jest-dom matchers, the MSW server lifecycle,
    // jsdom polyfills, and per-test cookie/cache resets.
    setupFiles: ['./src/test/setup.ts'],
    // Satisfies getBaseUrl() at module import time without hitting PROD or dev-URL paths.
    env: {
      VITE_API_URL: 'http://test.local',
    },
  },
});
