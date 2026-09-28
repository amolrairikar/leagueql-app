import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/my-team-nav.feature',
);

// The leading analytics nav entries, in the order the sidebar renders them.
const NAV_TITLES = new Set(['Home', 'My Team', 'Standings', 'Matchups']);

defineFeature(feature, (test) => {
  test('Entry placed under Home', ({ when, then, and }) => {
    when('I render the sidebar', async () => {
      server.use(leagueMetadata({ is_owner: true }));
      await renderRoute(
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>,
        { league: { leagueId: '100', platform: 'SLEEPER', seasons: ['2024'] } },
      );
      await screen.findByText('Home');
    });
    then(/^the nav items begin "(.*)"$/, (list) => {
      const expected = list.split(', ');
      const order = screen
        .getAllByRole('link')
        .map((a) => a.textContent?.trim() ?? '')
        .filter((t) => NAV_TITLES.has(t));
      expect(order.slice(0, expected.length)).toEqual(expected);
    });
    and(/^the "(.*)" nav item links to "(.*)"$/, (label, href) => {
      expect(screen.getByRole('link', { name: label })).toHaveAttribute(
        'href',
        href,
      );
    });
  });
});
