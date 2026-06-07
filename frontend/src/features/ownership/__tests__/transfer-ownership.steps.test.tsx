import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect, vi } from 'vitest';

import { TransferOwnershipDialog } from '../transfer-ownership-dialog';

import { postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/ownership/__tests__/transfer-ownership.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

defineFeature(feature, (test) => {
  const realClipboard = navigator.clipboard;
  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: realClipboard,
      configurable: true,
    });
  });

  test('Generating a token and copying it shows confirmation', ({
    given,
    when,
    then,
    and,
  }) => {
    const writeText = vi.fn().mockResolvedValue(undefined);

    given('the transfer ownership dialog is open', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText },
        configurable: true,
      });
      server.use(
        postJson('/leagues/100/transfer-token', {
          detail: 'Transfer token created',
          data: { token: 'TOK-123', expires_at: '2099-01-01T00:00:00Z' },
        }),
      );
      await renderRoute(
        <TransferOwnershipDialog open onOpenChange={vi.fn()} />,
        { league },
      );
    });

    when('I generate a transfer token', async () => {
      await userEvent.click(
        screen.getByRole('button', { name: /generate token/i }),
      );
    });

    then(/^I see the token "(.*)"$/, async (token) => {
      expect(await screen.findByDisplayValue(token)).toBeInTheDocument();
    });

    and(/^the copy button reads "(.*)"$/, (label) => {
      expect(
        screen.getByRole('button', { name: new RegExp(`^${label}$`, 'i') }),
      ).toBeInTheDocument();
    });

    when('I click the copy button', async () => {
      await userEvent.click(screen.getByRole('button', { name: /^copy$/i }));
    });

    then('the token is written to the clipboard', () => {
      expect(writeText).toHaveBeenCalledWith('TOK-123');
    });

    and(/^the copy button reads "(.*)"$/, async (label) => {
      expect(
        await screen.findByRole('button', {
          name: new RegExp(`^${label}$`, 'i'),
        }),
      ).toBeInTheDocument();
    });
  });
});
