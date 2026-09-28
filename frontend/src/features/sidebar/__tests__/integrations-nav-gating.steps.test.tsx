import { screen } from '@testing-library/react';
import {
  defineFeature,
  loadFeature,
  type DefineStepFunction,
} from 'jest-cucumber';
import { expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider } from '@/components/ui/sidebar';
import { setFlagsForTesting } from '@/lib/feature-flags';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/integrations-nav-gating.feature',
);

function givenFlag(given: DefineStepFunction) {
  given(/^the "(.*)" feature flag is (on|off)$/, (flag, state) => {
    setFlagsForTesting({ [flag]: state === 'on' });
  });
}

function whenRenderSidebar(when: DefineStepFunction) {
  when('I render the sidebar', async () => {
    server.use(leagueMetadata({ is_owner: true }));
    await renderRoute(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>,
      { league: { leagueId: '100', platform: 'SLEEPER', seasons: ['2024'] } },
    );
  });
}

defineFeature(feature, (test) => {
  test('Flag on shows the Integrations nav item', ({ given, when, then }) => {
    givenFlag(given);
    whenRenderSidebar(when);
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

  test('Flag off hides the Integrations nav item', ({ given, when, then }) => {
    givenFlag(given);
    whenRenderSidebar(when);
    then(/^I do not see an "(.*)" nav item$/, async (label) => {
      // Wait for the sidebar to settle before asserting absence.
      expect(await screen.findByText('Transactions')).toBeInTheDocument();
      expect(screen.queryByText(label)).not.toBeInTheDocument();
      expect(screen.queryByText('Community')).not.toBeInTheDocument();
    });
  });
});
