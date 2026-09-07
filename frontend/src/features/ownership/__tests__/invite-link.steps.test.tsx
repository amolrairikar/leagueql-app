import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { useState } from 'react';
import { expect, vi } from 'vitest';

import { InviteLinkDialog } from '../invite-link-dialog';

import { API, postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/ownership/__tests__/invite-link.feature',
);

const league = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

// Keeps the dialog mounted (as the sidebar does) while toggling `open`, so a
// close-then-reopen exercises what state survives across opens.
function InviteDialogHarness() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        reopen
      </button>
      <InviteLinkDialog open={open} onOpenChange={setOpen} />
    </>
  );
}

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
    and('I see a confirmation that the link was created', async () => {
      expect(await screen.findByRole('status')).toHaveTextContent(
        /new link created/i,
      );
    });
  });

  test('Regenerating replaces the link with a new one', ({
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
    and('the backend mints a fresh token on each request', () => {
      let mints = 0;
      server.use(
        http.post(`${API}/leagues/100/invite-token`, () => {
          mints += 1;
          return HttpResponse.json({
            detail: 'Invite link created',
            data: { token: `token-${mints}` },
          });
        }),
      );
    });
    when('I create the invite link', async () => {
      await userEvent.click(
        screen.getByRole('button', { name: /create invite link/i }),
      );
      // First mint shows the "Create new link" affordance.
      await screen.findByRole('button', { name: /create new link/i });
    });
    and('I create a new link', async () => {
      await userEvent.click(
        screen.getByRole('button', { name: /create new link/i }),
      );
    });
    then(/^I see a shareable link containing "(.*)"$/, async (fragment) => {
      const input =
        await screen.findByLabelText<HTMLInputElement>('Invite link');
      expect(input.value).toContain(fragment);
    });
  });

  test('Reopening the dialog shows the previously created link', ({
    given,
    and,
    when,
    then,
  }) => {
    given(
      /^the invite dialog harness is open for ESPN league "(.*)"$/,
      async () => {
        await renderRoute(<InviteDialogHarness />, { league });
      },
    );
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
      await screen.findByLabelText('Invite link');
    });
    and('I close the dialog and reopen it', async () => {
      await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
      // The link input unmounts with the closed dialog...
      expect(screen.queryByLabelText('Invite link')).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: /^reopen$/i }));
    });
    then(/^I see a shareable link containing "(.*)"$/, async (fragment) => {
      const input =
        await screen.findByLabelText<HTMLInputElement>('Invite link');
      expect(input.value).toContain(fragment);
    });
  });
});
