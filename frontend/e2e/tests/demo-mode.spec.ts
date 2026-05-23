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

testWithDemo.describe('Demo mode — page content', () => {
  testWithDemo('/home renders section headings and stat labels', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Champions', { exact: true })).toBeVisible();
    await expect(page.getByText('Final Standings Position by Season')).toBeVisible();
    await expect(page.getByText('Seasons played')).toBeVisible();
    await expect(page.getByText('Total matchups')).toBeVisible();
    await expect(page.getByText('Record score')).toBeVisible();
    await expect(page.getByText('Total members')).toBeVisible();
    await expect(page.getByText('Unique champions')).toBeVisible();
  });

  testWithDemo('/standings renders award cards, table headers, and chart', async ({ page }) => {
    await page.goto('/standings');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Season awards')).toBeVisible();
    await expect(page.getByText('Season Champion')).toBeVisible();
    await expect(page.getByText('High Scorer')).toBeVisible();
    await expect(page.getByText('Luckiest Team')).toBeVisible();
    await expect(page.getByText('Season standings')).toBeVisible();
    await expect(page.getByText('Owner')).toBeVisible();
    await expect(page.getByText('Record', { exact: true })).toBeVisible();
    await expect(page.getByText('PF/Game', { exact: true })).toBeVisible();
    await expect(page.getByText('PA/Game', { exact: true })).toBeVisible();
    await expect(page.getByText('Win %', { exact: true })).toBeVisible();
    await expect(page.getByText('Wins progression')).toBeVisible();
  });

  testWithDemo('/matchups renders week navigation tabs', async ({ page }) => {
    await page.goto('/matchups');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Wk 1', { exact: true })).toBeVisible();
  });

  testWithDemo('/playoff_bracket renders bracket round headers', async ({ page }) => {
    await page.goto('/playoff_bracket');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Semifinals')).toBeVisible();
    await expect(page.getByText('Championship')).toBeVisible();
  });

  testWithDemo('/player_records renders filter controls', async ({ page }) => {
    await page.goto('/player_records');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Season', { exact: true })).toBeVisible();
    await expect(page.getByText('Manager', { exact: true })).toBeVisible();
    await expect(page.getByText('All seasons')).toBeVisible();
    await expect(page.getByText('All managers')).toBeVisible();
  });

  testWithDemo('/matchup_records renders all record type cards', async ({ page }) => {
    await page.goto('/matchup_records');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Highest Team Score')).toBeVisible();
    await expect(page.getByText('Lowest Team Score')).toBeVisible();
    await expect(page.getByText('Highest Matchup Score')).toBeVisible();
    await expect(page.getByText('Lowest Matchup Score')).toBeVisible();
    await expect(page.getByText('Biggest Blowout')).toBeVisible();
    await expect(page.getByText('Closest Game')).toBeVisible();
  });

  testWithDemo('sidebar renders settings section with demo mode controls', async ({ page }) => {
    await page.goto('/home');
    await expect(page.getByText('Settings')).toBeVisible();
    await expect(page.getByText('Connect Your League')).toBeVisible();
    await expect(page.getByText('Exit Demo')).toBeVisible();
  });
});
