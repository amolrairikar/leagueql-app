import { createClerkClient } from '@clerk/backend';
import { test as base, expect } from '@playwright/test';

const clerkClient = createClerkClient({
  secretKey: process.env.CLERK_SECRET_KEY,
});

async function createAgentTaskWithRetry(maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await clerkClient.agentTasks.create({
        onBehalfOf: { userId: process.env.CLERK_TEST_USER_ID! },
        permissions: '*',
        agentName: 'e2e-test-agent',
        taskDescription: 'demo-mode-test',
        redirectUrl: 'http://localhost:5173/home',
      });
    } catch (err) {
      if (attempt === maxRetries - 1) throw err;
      await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
  throw new Error('unreachable');
}

export const testWithDemo = base.extend<{ demoPage: void }>({
  // auto: true so every testWithDemo test gets auth + demo cookies without explicit destructuring.
  // Two-step setup:
  //   1. Clerk Agent Task → visits agentTask.url → sets __session cookie → backend API calls succeed
  //   2. Demo cookies → isDemoMode() returns true → UI renders in demo mode (cookie-handler.ts:81)
  // Cookie values mirror demo-constants.ts — update both if demo data changes.
  demoPage: [
    async ({ page, context }, use) => {
      const agentTask = await createAgentTaskWithRetry();
      await page.goto(agentTask.url);
      await page.waitForURL('**/home');
      await context.addCookies([
        {
          name: 'demo_mode',
          value: 'true',
          domain: 'localhost',
          path: '/',
          sameSite: 'Strict',
        },
        {
          name: 'leagueId',
          value: '888888888',
          domain: 'localhost',
          path: '/',
          sameSite: 'Strict',
        },
        {
          name: 'leaguePlatform',
          value: 'SLEEPER',
          domain: 'localhost',
          path: '/',
          sameSite: 'Strict',
        },
        {
          name: 'leagueSeasons',
          value: encodeURIComponent(
            JSON.stringify(['2022', '2023', '2024', '2025']),
          ),
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
