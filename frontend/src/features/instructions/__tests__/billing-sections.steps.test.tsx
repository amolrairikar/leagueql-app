import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';

import InstructionsPage from '../instructions-page';

import { setFlagsForTesting } from '@/lib/feature-flags';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/instructions/__tests__/billing-sections.feature',
);

defineFeature(feature, (test) => {
  test('Billing enabled shows the subscription sections', ({
    given,
    when,
    then,
    and,
  }) => {
    given('billing is enabled', () => {
      setFlagsForTesting({ billing: true });
    });
    when('I open the user guide', async () => {
      await renderRoute(<InstructionsPage />, { route: '/docs' });
    });
    then(/^I see the "(.*)" guide section$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
    and(/^I see the "(.*)" guide section$/, (label) => {
      expect(screen.queryAllByText(label).length).toBeGreaterThan(0);
    });
    and(/^I see the "(.*)" guide section$/, (label) => {
      expect(screen.queryAllByText(label).length).toBeGreaterThan(0);
    });
  });

  test('Billing disabled hides the subscription sections', ({
    given,
    when,
    then,
    and,
  }) => {
    given('billing is disabled', () => {
      setFlagsForTesting({ billing: false });
    });
    when('I open the user guide', async () => {
      await renderRoute(<InstructionsPage />, { route: '/docs' });
    });
    // "Refresh League" is billing-independent, so the page still renders.
    then(/^I see the "(.*)" guide section$/, async (label) => {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    });
    and(/^I do not see the "(.*)" guide section$/, (label) => {
      expect(screen.queryAllByText(label)).toHaveLength(0);
    });
    and(/^I do not see the "(.*)" guide section$/, (label) => {
      expect(screen.queryAllByText(label)).toHaveLength(0);
    });
    and(/^I do not see the "(.*)" guide section$/, (label) => {
      expect(screen.queryAllByText(label)).toHaveLength(0);
    });
  });
});
