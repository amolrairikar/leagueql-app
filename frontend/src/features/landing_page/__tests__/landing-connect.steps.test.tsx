import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import LeagueQLLanding from '../landing-page';

import { API, postJson, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/landing_page/__tests__/landing-connect.feature',
);

defineFeature(feature, (test) => {
  test('Connecting an ESPN league I am not a member of opens the Join dialog', ({
    given,
    when,
    then,
  }) => {
    given('the ESPN league read is member-gated for me', async () => {
      // getLeague is a member-gated 403 until membership is verified, then 200.
      let getCalls = 0;
      server.use(
        http.get(`${API}/leagues/:id`, () => {
          getCalls += 1;
          if (getCalls === 1) {
            return HttpResponse.json(
              { detail: 'Not a member of this league' },
              { status: 403 },
            );
          }
          return HttpResponse.json({
            detail: 'Found league',
            data: {
              seasons: ['2024'],
              league_name: 'L',
              subscription_end_time: null,
              is_owner: false,
            },
          });
        }),
        postJson('/leagues/100/verify-membership', {
          detail: 'Membership verified',
        }),
      );
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

    then(/^I see the "(.*)" dialog$/, async (title) => {
      const dialog = await screen.findByRole('dialog');
      expect(
        within(dialog).getByRole('heading', { name: title }),
      ).toBeInTheDocument();
    });

    when('I verify my ESPN membership in the dialog', async () => {
      const dialog = screen.getByRole('dialog');
      await userEvent.type(
        within(dialog).getByPlaceholderText('Enter your SWID'),
        'swid-value',
      );
      await userEvent.type(
        within(dialog).getByPlaceholderText('Enter your ESPN S2 token'),
        's2cookie',
      );
      await userEvent.click(
        within(dialog).getByRole('button', { name: /join league/i }),
      );
    });

    then('I am routed to the home page', async () => {
      expect(await screen.findByText('HOME PAGE')).toBeInTheDocument();
    });
  });
});
