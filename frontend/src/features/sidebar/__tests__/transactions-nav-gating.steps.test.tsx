import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/transactions-nav-gating.feature',
);

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

defineFeature(feature, (test) => {
  async function renderSidebarFor(platform: Platform) {
    server.use(
      leagueMetadata({ subscription_end_time: isoIn(30), is_owner: true }),
    );
    await renderRoute(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>,
      { league: { leagueId: '100', platform, seasons: ['2024'] } },
    );
  }

  test('Sleeper leagues see the Transactions nav item', ({
    given,
    when,
    then,
  }) => {
    let platform: Platform = 'SLEEPER';
    given(/^the current league is on "(.*)"$/, (p) => {
      platform = p as Platform;
    });
    when('I render the sidebar', async () => {
      await renderSidebarFor(platform);
    });
    then(/^I see the "(.*)" nav item$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
  });

  test('ESPN leagues do not see the Transactions nav item', ({
    given,
    when,
    then,
  }) => {
    let platform: Platform = 'ESPN';
    given(/^the current league is on "(.*)"$/, (p) => {
      platform = p as Platform;
    });
    when('I render the sidebar', async () => {
      await renderSidebarFor(platform);
    });
    then(/^I do not see the "(.*)" nav item$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });
});
