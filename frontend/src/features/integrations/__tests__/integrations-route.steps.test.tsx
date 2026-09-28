import { screen } from '@testing-library/react';
import {
  defineFeature,
  loadFeature,
  type DefineStepFunction,
} from 'jest-cucumber';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import IntegrationsRoute from '../integrations-route';

import { integrationsList } from './fixtures';

import { setFlagsForTesting } from '@/lib/feature-flags';
import { server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/integrations/__tests__/integrations-route.feature',
);

function givenFlag(given: DefineStepFunction) {
  given(/^the "(.*)" feature flag is (on|off)$/, (flag, state) => {
    setFlagsForTesting({ [flag]: state === 'on' });
  });
}

function whenNavigate(when: DefineStepFunction) {
  when(/^I navigate to "(.*)"$/, async (route) => {
    await renderRoute(
      <Routes>
        <Route path="/integrations" element={<IntegrationsRoute />} />
        <Route path="/home" element={<p>Home page</p>} />
      </Routes>,
      { route },
    );
  });
}

defineFeature(feature, (test) => {
  test('Flag on renders the page', ({ given, and, when, then }) => {
    givenFlag(given);
    and('the integrations endpoint returns no integrations', () => {
      server.use(integrationsList([]));
    });
    whenNavigate(when);
    then('I see the Integrations page', () => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Integrations' }),
      ).toBeInTheDocument();
    });
  });

  test('Flag off redirects home', ({ given, when, then }) => {
    givenFlag(given);
    whenNavigate(when);
    then('I land on the home page', () => {
      expect(screen.getByText('Home page')).toBeInTheDocument();
      expect(
        screen.queryByRole('heading', { name: 'Integrations' }),
      ).not.toBeInTheDocument();
    });
  });
});
