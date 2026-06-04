import { act, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { afterEach, vi } from 'vitest';

import MigrateLeague from '../migrate-league';

import { API, leagueMetadata, leagueQuery, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/migrate_league/__tests__/migrate-league.feature',
);

const league = {
  leagueId: '100',
  platform: 'SLEEPER' as const,
  seasons: ['2024'],
};

const CURRENT_MANAGER = {
  display_name: 'Owner A',
  primary_owner_id: 'oA',
  team_name: 'Team A',
  season: '2024',
};

defineFeature(feature, (test) => {
  afterEach(() => vi.useRealTimers());

  test('A migration submits and polls to completion, then routes home', ({
    given,
    when,
    then,
  }) => {
    given('a migration that will complete successfully', () => {
      server.use(
        leagueMetadata({ seasons: ['2024'], league_name: 'My League' }),
        leagueQuery({ TEAMS: [CURRENT_MANAGER] }),
        http.post(`${API}/leagues/:id/espn_members`, () =>
          HttpResponse.json({
            data: [{ owner_id: 'm1', display_name: 'Manager One' }],
          }),
        ),
        http.post(`${API}/leagues/:id/migrate`, () =>
          HttpResponse.json(
            { detail: 'Migration started', data: { correlation_id: 'mig-1' } },
            { status: 202 },
          ),
        ),
        http.get(`${API}/jobs/:id`, () =>
          HttpResponse.json({
            detail: 'ok',
            data: {
              status: 'COMPLETED',
              failure_code: null,
              failure_reason: null,
            },
          }),
        ),
      );
    });

    when(
      /^I complete the migration wizard for ESPN league "(.*)"$/,
      async (id) => {
        const user = userEvent.setup();
        await renderRoute(
          <Routes>
            <Route path="/migrate_league" element={<MigrateLeague />} />
            <Route path="/home" element={<div>HOME PAGE</div>} />
          </Routes>,
          { route: '/migrate_league', league },
        );

        // Step 1 → 2
        await user.click(
          await screen.findByRole('button', { name: /^continue$/i }),
        );
        // Step 2: ESPN destination (the only option for a Sleeper source)
        await user.type(
          screen.getByPlaceholderText('Enter your ESPN league ID'),
          id,
        );
        await user.type(screen.getByPlaceholderText('e.g. 2025'), '2025');
        await user.type(
          screen.getByPlaceholderText('Enter your SWID'),
          '{{SWID}}',
        );
        await user.type(
          screen.getByPlaceholderText('Enter your ESPN S2'),
          's2',
        );
        await user.click(screen.getByRole('button', { name: /^next$/i }));
        // Step 3: map the one current manager to an ESPN account via the Select
        const trigger = await screen.findByRole('combobox');
        await user.click(trigger);
        await user.click(
          await screen.findByRole('option', { name: /Manager One/i }),
        );
        await user.click(screen.getByRole('button', { name: /^next$/i }));
        // Step 4 → submit; switch to fake timers to fast-forward the poll waits.
        vi.useFakeTimers();
        await act(async () => {
          fireEvent.click(
            screen.getByRole('button', { name: /^confirm migration$/i }),
          );
          await Promise.resolve();
        });
        // 5s initial delay + 1s poll + 1.5s post-success redirect delay.
        await act(async () => {
          await vi.advanceTimersByTimeAsync(9000);
        });
      },
    );

    then('I am routed to the home page', () => {
      expect(screen.getByText('HOME PAGE')).toBeInTheDocument();
    });
  });
});
