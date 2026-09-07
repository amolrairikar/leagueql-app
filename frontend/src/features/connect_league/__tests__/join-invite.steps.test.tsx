import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import JoinInvitePage from '../join-invite-page';

import { setClerkState } from '@/test/clerk-mock';
import { leagueMetadata, postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/connect_league/__tests__/join-invite.feature',
);

async function openInviteLink(leagueId: string) {
  const query = new URLSearchParams({ platform: 'ESPN', invite: 'tok' });
  await renderRoute(
    <Routes>
      <Route path="/join/:leagueId" element={<JoinInvitePage />} />
      <Route path="/home" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: `/join/${leagueId}?${query}` },
  );
}

defineFeature(feature, (test) => {
  test('A valid invite link joins the league and opens the dashboard', ({
    given,
    and,
    when,
    then,
  }) => {
    given('I am signed in', () => {
      setClerkState({ isSignedIn: true });
    });
    and('the invite token is accepted', () => {
      server.use(
        postJson('/leagues/100/accept-invite', { detail: 'Invite accepted' }),
        leagueMetadata({ seasons: ['2024'], is_owner: false }),
      );
    });
    when(
      /^I open the invite link for ESPN league "(.*)"$/,
      async (leagueId) => {
        await openInviteLink(leagueId);
      },
    );
    then('I am routed to the home page', async () => {
      expect(await screen.findByText('HOME PAGE')).toBeInTheDocument();
    });
  });

  test('A revoked invite link shows an inline error', ({
    given,
    and,
    when,
    then,
  }) => {
    given('I am signed in', () => {
      setClerkState({ isSignedIn: true });
    });
    and('the invite token is rejected as invalid', () => {
      server.use(
        postJson(
          '/leagues/100/accept-invite',
          { detail: 'Invalid invite link' },
          403,
        ),
      );
    });
    when(
      /^I open the invite link for ESPN league "(.*)"$/,
      async (leagueId) => {
        await openInviteLink(leagueId);
      },
    );
    then(/^I see an inline error "(.*)"$/, async (message) => {
      expect(await screen.findByText(new RegExp(message))).toBeInTheDocument();
    });
  });

  test('A signed-out caller is prompted to sign in first', ({
    given,
    when,
    then,
  }) => {
    given('I am signed out', () => {
      setClerkState({ isSignedIn: false });
    });
    when(
      /^I open the invite link for ESPN league "(.*)"$/,
      async (leagueId) => {
        await openInviteLink(leagueId);
      },
    );
    then('I am prompted to sign in', async () => {
      expect(await screen.findByTestId('clerk-sign-in')).toBeInTheDocument();
    });
  });
});
