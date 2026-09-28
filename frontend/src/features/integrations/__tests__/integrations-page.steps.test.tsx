import { screen, within } from '@testing-library/react';
import userEvent, { type UserEvent } from '@testing-library/user-event';
import {
  defineFeature,
  loadFeature,
  type DefineStepFunction,
} from 'jest-cucumber';
import { expect } from 'vitest';

import IntegrationsPage from '../integrations-page';

import {
  ALL_INTEGRATIONS,
  HISTORIAN,
  POWER_SHEET,
  RECAP_BOT,
  integrationsList,
  integrationsListError,
} from './fixtures';

import { server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/integrations/__tests__/integrations-page.feature',
);

let user: UserEvent;

function browseRegion() {
  return screen.getByRole('region', { name: 'Browse integrations' });
}

function cardTitles(): string[] {
  return within(browseRegion())
    .queryAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent ?? '');
}

function givenThreeIntegrations(given: DefineStepFunction) {
  given(
    /^the integrations endpoint returns three integrations with "(.*)" featured$/,
    () => {
      server.use(integrationsList(ALL_INTEGRATIONS));
    },
  );
}

function whenPageOpens(when: DefineStepFunction) {
  when('I open the integrations page', async () => {
    user = userEvent.setup();
    await renderRoute(<IntegrationsPage />);
  });
}

defineFeature(feature, (test) => {
  test('Approved integrations render with the featured one highlighted', ({
    given,
    when,
    then,
    and,
  }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    then('I see the page heading and the three how-it-works steps', () => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Integrations' }),
      ).toBeInTheDocument();
      const steps = within(
        screen.getByRole('region', { name: 'How it works' }),
      ).getAllByRole('heading', { level: 2 });
      expect(steps.map((s) => s.textContent)).toEqual([
        'Export your league',
        "Analyze your league's data",
        'Share what you built',
      ]);
      expect(
        screen.getByText(
          'Upload it to an AI assistant, import it into a sheet, or point a script at it.',
        ),
      ).toBeInTheDocument();
    });

    and(/^the featured card shows "(.*)"$/, (name) => {
      const featured = screen.getByRole('region', {
        name: 'Featured integration',
      });
      expect(within(featured).getByRole('heading', { name })).toBeVisible();
    });

    and(/^the grid shows (\d+) integration cards$/, (count) => {
      expect(cardTitles()).toHaveLength(Number(count));
    });
  });

  test('No featured integration', ({ given, when, then, and }) => {
    given(
      'the integrations endpoint returns integrations with none featured',
      () => {
        server.use(integrationsList([RECAP_BOT, POWER_SHEET]));
      },
    );
    whenPageOpens(when);

    then('no featured card is shown', () => {
      expect(
        screen.queryByRole('region', { name: 'Featured integration' }),
      ).not.toBeInTheDocument();
    });

    and(/^the grid shows (\d+) integration cards$/, (count) => {
      expect(cardTitles()).toHaveLength(Number(count));
    });
  });

  test('No integrations yet', ({ given, when, then }) => {
    given('the integrations endpoint returns no integrations', () => {
      server.use(integrationsList([]));
    });
    whenPageOpens(when);

    then('I see the empty state inviting a first submission', () => {
      expect(
        screen.getByText('No integrations yet. Be the first to submit one.'),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole('region', { name: 'Browse integrations' }),
      ).not.toBeInTheDocument();
    });
  });

  test('Listing fails', ({ given, when, then, and }) => {
    given('the integrations endpoint fails with a server error', () => {
      server.use(integrationsListError(502));
    });
    whenPageOpens(when);

    then('I see an inline error about loading integrations', () => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        "Couldn't load integrations right now. Try again in a few minutes.",
      );
    });

    and('the submit button is still available', () => {
      expect(
        screen.getByRole('button', { name: /submit your integration/i }),
      ).toBeEnabled();
    });
  });

  test('Filter by category', ({ given, when, then, and }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    and(/^I select the "(.*)" category$/, async (label) => {
      await user.click(
        within(
          screen.getByRole('group', { name: 'Filter by category' }),
        ).getByRole('button', { name: new RegExp(`^${label}`) }),
      );
    });

    then(/^the grid shows only "(.*)"$/, (name) => {
      expect(cardTitles()).toEqual([name]);
    });

    and(/^the result count reads "(.*)"$/, (text) => {
      expect(within(browseRegion()).getByText(text)).toBeInTheDocument();
    });
  });

  test('Search by view name', ({ given, when, then, and }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    and(/^I search for "(.*)"$/, async (query) => {
      await user.type(
        screen.getByRole('searchbox', { name: 'Search integrations' }),
        query,
      );
    });

    then(/^the grid shows only "(.*)"$/, (name) => {
      expect(cardTitles()).toEqual([name]);
    });
  });

  test('No matches', ({ given, when, then, and }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    and(/^I search for "(.*)"$/, async (query) => {
      await user.type(
        screen.getByRole('searchbox', { name: 'Search integrations' }),
        query,
      );
    });

    then('I see the no-matches message', () => {
      expect(cardTitles()).toEqual([]);
      expect(
        screen.getByText(
          'No integrations match. Try another category or search.',
        ),
      ).toBeInTheDocument();
    });
  });

  test('Open integration details', ({ given, when, then, and }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    and(/^I open the "(.*)" card$/, async (name) => {
      const card = within(browseRegion())
        .getByRole('heading', { level: 3, name })
        .closest('button');
      await user.click(card!);
    });

    then(
      /^the detail dialog shows the setup steps and files for "(.*)"$/,
      (name) => {
        const dialog = screen.getByRole('dialog');
        expect(within(dialog).getByRole('heading', { name })).toBeVisible();
        for (const step of RECAP_BOT.setup_steps) {
          expect(within(dialog).getByText(step)).toBeInTheDocument();
        }
        expect(
          within(dialog).getByText('<season>_matchups.json'),
        ).toBeInTheDocument();
      },
    );

    and(/^the detail dialog links to "(.*)"$/, (href) => {
      const link = within(screen.getByRole('dialog')).getByRole('link', {
        name: /open project/i,
      });
      expect(link).toHaveAttribute('href', href);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    and('the detail dialog has no prompt section', () => {
      const dialog = screen.getByRole('dialog');
      expect(within(dialog).queryByText('Prompt')).not.toBeInTheDocument();
      expect(
        within(dialog).queryByRole('button', { name: /copy prompt/i }),
      ).not.toBeInTheDocument();
    });
  });

  test("Copy an integration's prompt", ({ given, when, then, and }) => {
    givenThreeIntegrations(given);
    whenPageOpens(when);

    and('I click "View setup" on the featured card', async () => {
      await user.click(screen.getByRole('button', { name: 'View setup' }));
    });

    and('I click "Copy prompt"', async () => {
      await user.click(
        within(screen.getByRole('dialog')).getByRole('button', {
          name: /copy prompt/i,
        }),
      );
    });

    then('the prompt is copied to the clipboard', async () => {
      expect(await navigator.clipboard.readText()).toBe(HISTORIAN.prompt);
    });

    and(/^the copy button reads "(.*)"$/, async (label) => {
      expect(
        await within(screen.getByRole('dialog')).findByRole('button', {
          name: label,
        }),
      ).toBeInTheDocument();
    });
  });
});
