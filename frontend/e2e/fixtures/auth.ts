import { test as base, expect } from '@playwright/test';

export const testWithDemo = base.extend<{ demoPage: void }>({
  // auto: true so every testWithDemo test gets the demo cookies without explicit destructuring
  demoPage: [
    async ({ context }, use) => {
      // Cookie values mirror demo-constants.ts — update both if demo data changes.
      // demo_mode=true is the exact string isDemoMode() checks (cookie-handler.ts:81).
      await context.addCookies([
        { name: 'demo_mode', value: 'true', domain: 'localhost', path: '/', sameSite: 'Strict' },
        { name: 'leagueId', value: '999999999', domain: 'localhost', path: '/', sameSite: 'Strict' },
        { name: 'leaguePlatform', value: 'ESPN', domain: 'localhost', path: '/', sameSite: 'Strict' },
        {
          name: 'leagueSeasons',
          value: encodeURIComponent(JSON.stringify(['2022', '2023', '2024'])),
          domain: 'localhost',
          path: '/',
          sameSite: 'Strict',
        },
      ]);
      await use();
    },
    { auto: true },
  ],
});

export { expect };
