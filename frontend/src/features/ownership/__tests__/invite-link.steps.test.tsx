import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect, vi } from 'vitest';

import { InviteLinkDialog } from '../invite-link-dialog';

import { postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/ownership/__tests__/invite-link.feature',
);

const league = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

defineFeature(feature, (test) => {
  test('Creating an invite link shows a shareable /join URL', ({
    given,
    and,
    when,
    then,
  }) => {
    given(/^the invite dialog is open for ESPN league "(.*)"$/, async () => {
      await renderRoute(<InviteLinkDialog open onOpenChange={vi.fn()} />, {
        league,
      });
    });
    and(/^the backend mints an invite token "(.*)"$/, (token) => {
      server.use(
        postJson('/leagues/100/invite-token', {
          detail: 'Invite link created',
          data: { token },
        }),
      );
    });
    when('I create the invite link', async () => {
      await userEvent.click(
        screen.getByRole('button', { name: /create invite link/i }),
      );
    });
    then(/^I see a shareable link containing "(.*)"$/, async (fragment) => {
      const input =
        await screen.findByLabelText<HTMLInputElement>('Invite link');
      expect(input.value).toContain(fragment);
    });
  });
});
