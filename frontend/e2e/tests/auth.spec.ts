import { test, expect } from '@playwright/test';

const PROTECTED_ROUTES = [
  '/league',
  '/connect_league',
  '/home',
  '/standings',
  '/matchups',
  '/playoff_bracket',
  '/manager_comparison',
  '/manager_history',
  '/player_records',
  '/matchup_records',
  '/draft_recap',
];

test.describe('Unauthenticated behavior', () => {
  test('landing page loads without authentication', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Connect Your League' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'View Demo' })).toBeVisible();
  });

  test('privacy page is accessible without authentication', async ({ page }) => {
    await page.goto('/privacy');
    await expect(page).not.toHaveURL('/');
  });

  test('all protected routes redirect to landing page when unauthenticated', async ({ page }) => {
    for (const route of PROTECTED_ROUTES) {
      await page.goto(route);
      await expect(page).toHaveURL('/');
    }
  });

  test('"Connect Your League" opens the sign-in dialog', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Connect Your League' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('"View Demo" navigates to /home with demo banner', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'View Demo' }).click();
    await expect(page).toHaveURL('/home');
    await expect(page.getByText('Demo Mode')).toBeVisible();
  });
});
