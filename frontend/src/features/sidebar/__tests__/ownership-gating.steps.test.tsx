import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import { setFlagsForTesting } from '@/lib/feature-flags';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/ownership-gating.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

defineFeature(feature, (test) => {
  async function renderSidebar() {
    await renderRoute(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>,
      { league },
    );
  }

  test('The owner sees the owner-only actions', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I am the owner of the current league', () => {
      server.use(
        leagueMetadata({ subscription_end_time: isoIn(30), is_owner: true }),
      );
    });
    when('I render the sidebar', renderSidebar);
    then(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });

  test('A non-owner sees no owner actions', ({ given, when, then, and }) => {
    given('I am not the owner of the current league', () => {
      server.use(
        leagueMetadata({ subscription_end_time: isoIn(30), is_owner: false }),
      );
    });
    when('I render the sidebar', renderSidebar);
    then(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });

  test('Billing disabled hides Manage Subscription for the owner (FE-026)', ({
    given,
    and,
    when,
    then,
  }) => {
    given('billing is disabled', () => {
      setFlagsForTesting({ billing: false });
    });
    and('I am the owner of the current league', () => {
      server.use(
        leagueMetadata({ subscription_end_time: isoIn(30), is_owner: true }),
      );
    });
    when('I render the sidebar', renderSidebar);
    then(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });
});
