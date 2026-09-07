import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/ownership-gating.feature',
);

const espnLeague = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

const sleeperLeague = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

defineFeature(feature, (test) => {
  async function renderSidebar(
    league: typeof espnLeague | typeof sleeperLeague,
  ) {
    await renderRoute(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>,
      { league },
    );
  }

  test('The ESPN owner sees the owner-only actions', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I am the owner of the current ESPN league', () => {
      server.use(leagueMetadata({ is_owner: true }));
    });
    when('I render the sidebar', () => renderSidebar(espnLeague));
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
    given('I am not the owner of the current ESPN league', () => {
      server.use(leagueMetadata({ is_owner: false }));
    });
    when('I render the sidebar', () => renderSidebar(espnLeague));
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

  test('A Sleeper owner does not see Refresh League', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I am the owner of the current Sleeper league', () => {
      server.use(leagueMetadata({ is_owner: true }));
    });
    when('I render the sidebar', () => renderSidebar(sleeperLeague));
    then(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I see the "(.*)" action$/, async (label) => {
      expect(await screen.findByText(label)).toBeInTheDocument();
    });
    and(/^I do not see the "(.*)" action$/, (label) => {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    });
  });
});
