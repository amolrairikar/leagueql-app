import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/integrations-nav.feature',
);

defineFeature(feature, (test) => {
  test('The sidebar shows the Integrations nav item', ({ when, then }) => {
    when('I render the sidebar', async () => {
      server.use(leagueMetadata({ is_owner: true }));
      await renderRoute(
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>,
        { league: { leagueId: '100', platform: 'SLEEPER', seasons: ['2024'] } },
      );
    });
    then(
      /^I see the "(.*)" group with an "(.*)" link to "(.*)"$/,
      async (group, label, href) => {
        expect(await screen.findByText(group)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: label })).toHaveAttribute(
          'href',
          href,
        );
      },
    );
  });
});
