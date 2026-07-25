import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect } from 'vitest';

import { AppSidebar } from '../app-sidebar';
import { HeaderAccount } from '../header-account';

import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/sidebar/__tests__/account-menu-placement.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

// The mocked Clerk UserButton renders <button>user</button> (src/test/clerk-mock.tsx).
function accountButtons() {
  return screen.queryAllByRole('button', { name: 'user' });
}

// useIsMobile() keys off window.innerWidth (< 768 → mobile); jsdom defaults to 1024.
const realInnerWidth = window.innerWidth;

async function renderLayout() {
  server.use(leagueMetadata({ is_owner: true }));
  await renderRoute(
    <SidebarProvider>
      <SidebarTrigger />
      <HeaderAccount />
      <AppSidebar />
    </SidebarProvider>,
    { league },
  );
}

defineFeature(feature, (test) => {
  afterEach(() => {
    window.innerWidth = realInnerWidth;
  });

  test('On mobile the account menu is in the header, not the sidebar sheet', ({
    given,
    then,
    and,
  }) => {
    given('I am signed in on a mobile viewport', async () => {
      window.innerWidth = 480;
      await renderLayout();
    });

    then('the account menu is present in the header', () => {
      // With the sheet closed, the header account button is accessible; the
      // sidebar footer renders none on mobile, so there is exactly one.
      expect(accountButtons()).toHaveLength(1);
    });

    and(
      'it is not inside the sidebar sheet when the sheet is opened',
      async () => {
        await userEvent.click(
          screen.getByRole('button', { name: /toggle sidebar/i }),
        );
        const sheet = await screen.findByRole('dialog');
        expect(
          within(sheet).queryByRole('button', { name: 'user' }),
        ).not.toBeInTheDocument();
      },
    );
  });

  test('On desktop the account menu stays in the sidebar', ({
    given,
    then,
  }) => {
    given('I am signed in on a desktop viewport', async () => {
      window.innerWidth = 1280;
      await renderLayout();
    });

    then('the account menu is shown exactly once', () => {
      // The sidebar footer renders it on desktop; HeaderAccount renders nothing.
      expect(accountButtons()).toHaveLength(1);
    });
  });
});
