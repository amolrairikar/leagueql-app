import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';

import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/mobile-subscription-dialog.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

function isoIn(days: number): string {
  return new Date(Date.now() + days * 86400000).toISOString();
}

// useIsMobile() keys off window.innerWidth (< 768 → mobile); jsdom defaults to
// 1024, so force a phone width for the duration of the test.
const realInnerWidth = window.innerWidth;

defineFeature(feature, (test) => {
  afterEach(() => {
    window.innerWidth = realInnerWidth;
  });

  test('The dialog stays open after the mobile sidebar closes', ({
    given,
    when,
    then,
    and,
  }) => {
    given('I am on a mobile viewport with an active subscription', async () => {
      window.innerWidth = 480;
      server.use(leagueMetadata({ subscription_end_time: isoIn(30) }));
      await renderRoute(
        <SidebarProvider>
          <SidebarTrigger />
          <AppSidebar />
        </SidebarProvider>,
        { league },
      );
    });

    when('I open the sidebar and select Manage Subscription', async () => {
      // Open the mobile sheet so its menu (and the Manage Subscription button)
      // mounts, then click the button — which closes the sheet and opens the dialog.
      await userEvent.click(
        screen.getByRole('button', { name: /toggle sidebar/i }),
      );
      await userEvent.click(
        await screen.findByRole('button', { name: /manage subscription/i }),
      );
    });

    then('the Manage Subscription dialog is open', async () => {
      const dialog = await screen.findByRole('dialog');
      expect(
        within(dialog).getByText('Manage Subscription'),
      ).toBeInTheDocument();
      expect(
        within(dialog).getByText(/your subscription is active/i),
      ).toBeInTheDocument();
    });

    and('the sidebar sheet has closed', () => {
      // A sidebar-only menu item is gone once the sheet unmounts, proving the
      // dialog above survived the sheet closing rather than being torn down with it.
      expect(screen.queryByText('Refresh League')).not.toBeInTheDocument();
    });
  });
});
