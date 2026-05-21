import { testWithDemo, expect } from '../fixtures/auth';

const NAV_ITEMS = [
  { title: 'Home', url: '/home' },
  { title: 'Standings', url: '/standings' },
  { title: 'Matchups', url: '/matchups' },
  { title: 'Playoff Bracket', url: '/playoff_bracket' },
  { title: 'Manager Comparison', url: '/manager_comparison' },
  { title: 'Manager History', url: '/manager_history' },
  { title: 'Draft Recap', url: '/draft_recap' },
  { title: 'Player Records', url: '/player_records' },
  { title: 'Matchup Records', url: '/matchup_records' },
];

testWithDemo.describe('Demo mode — protected pages', () => {
  testWithDemo('demo banner is visible on /home', async ({ page }) => {
    await page.goto('/home');
    await expect(page).toHaveURL('/home');
    await expect(page.getByText('Demo Mode')).toBeVisible();
  });

  testWithDemo('demo banner is visible on /standings', async ({ page }) => {
    await page.goto('/standings');
    await expect(page).toHaveURL('/standings');
    await expect(page.getByText('Demo Mode')).toBeVisible();
  });

  testWithDemo('demo banner is visible on /matchups', async ({ page }) => {
    await page.goto('/matchups');
    await expect(page).toHaveURL('/matchups');
    await expect(page.getByText('Demo Mode')).toBeVisible();
  });

  testWithDemo('all sidebar nav links are visible', async ({ page }) => {
    await page.goto('/home');
    for (const item of NAV_ITEMS) {
      await expect(page.getByRole('link', { name: item.title })).toBeVisible();
    }
  });

  testWithDemo('sidebar nav links navigate to correct routes', async ({ page }) => {
    await page.goto('/home');
    await page.getByRole('link', { name: 'Standings' }).click();
    await expect(page).toHaveURL('/standings');
  });

  testWithDemo('/league renders league selection page', async ({ page }) => {
    await page.goto('/league');
    await expect(page).toHaveURL('/league');
    // /league uses Header + LeagueSelection, not AppLayout, so no demo banner.
    // CardTitle renders as a div, not a semantic heading element.
    await expect(page.getByText('Your League')).toBeVisible();
  });

  testWithDemo('no protected page redirects to landing page', async ({ page }) => {
    // URL check is sufficient — if we stayed on the route, ProtectedRoute allowed access
    for (const item of NAV_ITEMS) {
      await page.goto(item.url);
      await expect(page).toHaveURL(item.url);
    }
  });
});
