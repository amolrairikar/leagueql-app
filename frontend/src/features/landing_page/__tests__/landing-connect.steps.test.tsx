import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import LeagueQLLanding from '../landing-page';

import { leagueMetadataError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/landing_page/__tests__/landing-connect.feature',
);

defineFeature(feature, (test) => {
  test('Connecting an ESPN league I am not a member of shows invite-link guidance', ({
    given,
    when,
    then,
  }) => {
    given('the ESPN league read is member-gated for me', async () => {
      // The read is a member-gated 403 and there is no cookie self-serve path —
      // the caller is directed to an owner's invite link.
      server.use(leagueMetadataError(403));
      window.history.pushState({}, '', '/?connect=true');
      await renderRoute(
        <Routes>
          <Route path="/" element={<LeagueQLLanding />} />
          <Route path="/home" element={<div>HOME PAGE</div>} />
        </Routes>,
        { route: '/' },
      );
    });

    when('I submit an ESPN league ID from the landing page', async () => {
      // Platform defaults to ESPN on the landing connect form.
      await userEvent.type(
        await screen.findByPlaceholderText('League ID'),
        '100',
      );
      await userEvent.click(screen.getByRole('button', { name: /^connect$/i }));
    });

    then(/^I see invite-link guidance "(.*)"$/, async (message) => {
      expect(await screen.findByText(new RegExp(message))).toBeInTheDocument();
    });
  });
});
