import fs from 'fs';
import path from 'path';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { loadEnv, type Plugin } from 'vite';
import svgr from 'vite-plugin-svgr';
import { defineConfig } from 'vitest/config';

/**
 * Substitute the `__VITE_DEV_API_URL__` token in the emitted `dist/_headers` (frontend/security-headers) with
 * the build-time `VITE_DEV_API_URL` so the dev/preview API Gateway origin is not hardcoded
 * in the CSP `connect-src`. When the var is unset (e.g. production builds) the token — and
 * its surrounding whitespace — is removed, leaving only the production origins.
 */
function headersDevApiOrigin(): Plugin {
  let outDir = 'dist';
  let devApiUrl = '';
  return {
    name: 'headers-dev-api-origin',
    apply: 'build',
    configResolved(config) {
      outDir = config.build.outDir;
      devApiUrl =
        loadEnv(config.mode, config.root, 'VITE_').VITE_DEV_API_URL ?? '';
    },
    closeBundle() {
      const headersPath = path.resolve(outDir, '_headers');
      /* eslint-disable security/detect-non-literal-fs-filename --
         Build-time only; path is derived from the fixed build outDir. */
      if (!fs.existsSync(headersPath)) return;
      const contents = fs.readFileSync(headersPath, 'utf8');
      const replacement = devApiUrl ? ` ${devApiUrl} ` : ' ';
      fs.writeFileSync(
        headersPath,
        contents.replace(/ ?__VITE_DEV_API_URL__ ?/g, replacement),
      );
      /* eslint-enable security/detect-non-literal-fs-filename */
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), svgr(), headersDevApiOrigin()],
  build: {
    rolldownOptions: {
      output: {
        // Keep rarely-changing vendor code in stable, separately cached chunks
        // (frontend/route-code-splitting). Everything else follows Rolldown's default split.
        codeSplitting: {
          groups: [
            // Tiny utilities shared by app code and recharts; keep them out of the recharts chunk
            // so the landing page never has to fetch it.
            {
              name: 'vendor-common',
              test: /node_modules\/clsx\//,
              priority: 50,
            },
            {
              name: 'vendor-react',
              test: /node_modules\/(react|react-dom|scheduler)\//,
              priority: 40,
            },
            {
              name: 'vendor-recharts',
              test: /node_modules\/(recharts|d3-|victory-vendor)/,
              priority: 30,
            },
            {
              name: 'vendor-clerk',
              test: /node_modules\/@clerk\//,
              priority: 20,
            },
            {
              name: 'vendor-otel',
              test: /node_modules\/@opentelemetry\//,
              priority: 10,
            },
          ],
        },
      },
    },
  },
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
