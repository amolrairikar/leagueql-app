import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { afterEach, expect, vi } from 'vitest';

import { MembershipGuard } from '../membership-guard';

import { requestEspnCookies } from '@/lib/espn-extension';
import { leagueMetadataError, postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

vi.mock('@/lib/espn-extension', async (importActual) => ({
  ...(await importActual<typeof import('@/lib/espn-extension')>()),
  requestEspnCookies: vi.fn(),
}));

const feature = loadFeature(
  'src/features/ownership/__tests__/membership-verification.feature',
);

const league = {
  leagueId: '100',
  platform: 'ESPN' as const,
  seasons: ['2024'],
};

async function openGuardedLeague() {
  // Flag the page as having the extension so the dialog's autofill button renders.
  document.documentElement.setAttribute('data-leagueql-espn-extension', '1');
  await renderRoute(
    <MembershipGuard>
      <div>Protected dashboard</div>
    </MembershipGuard>,
    { league },
  );
}

async function autofillAndJoin() {
  const dialog = await screen.findByRole('dialog');
  await userEvent.click(
    within(dialog).getByRole('button', { name: /autofill cookies from espn/i }),
  );
  // Autofill populates the inputs (enabling the Join button) before we submit.
  await within(dialog).findByDisplayValue('{SWID}');
  await userEvent.click(
    within(dialog).getByRole('button', { name: /join league/i }),
  );
}

defineFeature(feature, (test) => {
  const cookies = vi.mocked(requestEspnCookies);

  afterEach(() => {
    document.documentElement.removeAttribute('data-leagueql-espn-extension');
  });

  test('A non-member verifies and unlocks the dashboard', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the ESPN league returns 403 for the current caller', () => {
      server.use(leagueMetadataError(403));
    });
    and('the extension can supply valid ESPN cookies', () => {
      cookies.mockResolvedValue({ swid: '{SWID}', espnS2: 's2cookie' });
    });
    when(
      'I open the ESPN league behind the membership guard',
      openGuardedLeague,
    );
    then(/^I see the verification prompt "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('verification succeeds', () => {
      server.use(
        postJson('/leagues/100/verify-membership', {
          detail: 'Membership verified',
        }),
      );
    });
    and('I autofill my cookies and join in the dialog', autofillAndJoin);
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });

  test('Rejected cookies show an inline error', ({
    given,
    and,
    when,
    then,
  }) => {
    given('the ESPN league returns 403 for the current caller', () => {
      server.use(leagueMetadataError(403));
    });
    and('the extension can supply valid ESPN cookies', () => {
      cookies.mockResolvedValue({ swid: '{SWID}', espnS2: 's2cookie' });
    });
    when(
      'I open the ESPN league behind the membership guard',
      openGuardedLeague,
    );
    then(/^I see the verification prompt "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
    when('verification is rejected by ESPN', () => {
      server.use(
        postJson(
          '/leagues/100/verify-membership',
          { detail: 'Could not verify ESPN league membership' },
          403,
        ),
      );
    });
    and('I autofill my cookies and join in the dialog', autofillAndJoin);
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(message)).toBeInTheDocument();
    });
  });
});
