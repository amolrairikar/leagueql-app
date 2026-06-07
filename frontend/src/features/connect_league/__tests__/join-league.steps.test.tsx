import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect, vi } from 'vitest';

import { JoinLeagueDialog } from '../join-league-dialog';

import { ESPN_EXTENSION_URL, requestEspnCookies } from '@/lib/espn-extension';
import { postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

vi.mock('@/lib/espn-extension', async (importActual) => ({
  ...(await importActual<typeof import('@/lib/espn-extension')>()),
  requestEspnCookies: vi.fn(),
}));

const feature = loadFeature(
  'src/features/connect_league/__tests__/join-league.feature',
);

defineFeature(feature, (test) => {
  const cookies = vi.mocked(requestEspnCookies);

  afterEach(() => {
    document.documentElement.removeAttribute('data-leagueql-espn-extension');
  });

  test('Autofilled cookies that ESPN rejects show an inline error', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the Join League dialog is open for an ESPN league', async () => {
      // Flag the page as having the extension so the autofill button renders.
      document.documentElement.setAttribute(
        'data-leagueql-espn-extension',
        '1',
      );
      await renderRoute(
        <JoinLeagueDialog open onOpenChange={vi.fn()} leagueId="100" />,
      );
    });

    and('the extension supplies ESPN cookies', () => {
      cookies.mockResolvedValue({ swid: '{SWID}', espnS2: 's2cookie' });
    });

    and('ESPN will reject the cookies', () => {
      server.use(
        postJson(
          '/leagues/100/verify-membership',
          { detail: 'Could not verify ESPN league membership' },
          403,
        ),
      );
    });

    when('I autofill my cookies and try to join', async () => {
      await userEvent.click(
        screen.getByRole('button', { name: /autofill cookies from espn/i }),
      );
      // Autofill populates the inputs, enabling the Join button.
      expect(await screen.findByDisplayValue('{SWID}')).toBeInTheDocument();
      await userEvent.click(
        screen.getByRole('button', { name: /join league/i }),
      );
    });

    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });

  test('Without the extension, an install link is shown instead of the autofill button', ({
    given,
    then,
    and,
  }) => {
    given(
      'the Join League dialog is open without the extension installed',
      async () => {
        await renderRoute(
          <JoinLeagueDialog open onOpenChange={vi.fn()} leagueId="100" />,
        );
      },
    );

    then('there is no autofill button', () => {
      expect(
        screen.queryByRole('button', { name: /autofill cookies from espn/i }),
      ).not.toBeInTheDocument();
    });

    and(
      'I see a link to install the LeagueQL ESPN Cookie Helper extension',
      () => {
        expect(
          screen.getByRole('link', {
            name: /LeagueQL ESPN Cookie Helper extension/i,
          }),
        ).toHaveAttribute('href', ESPN_EXTENSION_URL);
      },
    );
  });
});
