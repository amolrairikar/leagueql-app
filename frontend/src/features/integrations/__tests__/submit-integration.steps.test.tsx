import { screen, within } from '@testing-library/react';
import userEvent, { type UserEvent } from '@testing-library/user-event';
import {
  defineFeature,
  loadFeature,
  type DefineStepFunction,
} from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { expect, vi } from 'vitest';

import { SubmitIntegrationDialog } from '../submit-integration-dialog';
import type { IntegrationSubmission } from '../types';

import { API, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/integrations/__tests__/submit-integration.feature',
);

let user: UserEvent;
let sentBody: IntegrationSubmission | null = null;

function givenDialogOpen(given: DefineStepFunction) {
  given('the submit dialog is open', async () => {
    sentBody = null;
    user = userEvent.setup();
    await renderRoute(<SubmitIntegrationDialog open onOpenChange={vi.fn()} />);
  });
}

async function chooseCategory(label: string) {
  await user.click(screen.getByRole('combobox', { name: 'Category' }));
  await user.click(await screen.findByRole('option', { name: label }));
}

function whenFillComplete(when: DefineStepFunction) {
  when(
    /^I fill in a complete "(.*)" submission named "(.*)"$/,
    async (category, name) => {
      await user.type(screen.getByLabelText('Integration Name'), name);
      await chooseCategory(category);
      await user.type(
        screen.getByLabelText('Link'),
        'https://github.com/example/trade-grader',
      );
      await user.click(screen.getByRole('checkbox', { name: 'transactions' }));
      await user.click(screen.getByRole('checkbox', { name: 'matchups' }));
      await user.type(
        screen.getByLabelText('What it does'),
        'Grades every trade.',
      );
      await user.type(
        screen.getByLabelText('Step 1'),
        'Fork the repo.{enter}Add your webhook secret.',
      );
    },
  );
}

function whenClickSubmit(when: DefineStepFunction) {
  when('I click "Submit for review"', async () => {
    await user.click(screen.getByRole('button', { name: 'Submit for review' }));
  });
}

function submitEndpoint(status: number, body: object) {
  server.use(
    http.post(`${API}/integrations`, async ({ request }) => {
      sentBody = (await request.json()) as IntegrationSubmission;
      return HttpResponse.json(body, { status });
    }),
  );
}

function givenRejection(given: DefineStepFunction) {
  given(
    /^the submit endpoint will reject the submission with status (\d+) and message "(.*)"$/,
    (status, message) => {
      submitEndpoint(Number(status), { detail: message });
    },
  );
}

function thenErrorKeepsValues(
  then: DefineStepFunction,
  and: DefineStepFunction,
) {
  then(/^the dialog shows the error "(.*)"$/, async (message) => {
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
  });

  and(/^the name field still reads "(.*)"$/, (name) => {
    expect(screen.getByLabelText('Integration Name')).toHaveValue(name);
  });
}

defineFeature(feature, (test) => {
  test('Successful submission', ({ given, when, then, and }) => {
    givenDialogOpen(given);
    and(
      /^the submit endpoint will accept the submission as issue (\d+)$/,
      (issue) => {
        submitEndpoint(201, {
          detail: 'Integration submitted for review',
          data: { issue_number: Number(issue) },
        });
      },
    );
    whenFillComplete(when);
    whenClickSubmit(when);

    then(
      'the dialog shows "Submitted for review" and that the submission was received',
      async () => {
        const dialog = screen.getByRole('dialog');
        expect(
          await within(dialog).findByText('Submitted for review'),
        ).toBeInTheDocument();
        expect(
          within(dialog).getByText(/we have received your submission/i),
        ).toBeVisible();
        expect(within(dialog).queryByText(/#\d+/)).not.toBeInTheDocument();
      },
    );

    and(
      /^the submission sent "(.*)" with views "(.*)" and no prompt$/,
      (name, views) => {
        expect(sentBody).toEqual({
          name,
          category: 'bot',
          link: 'https://github.com/example/trade-grader',
          views: views.split(','),
          description: 'Grades every trade.',
          setup_steps: ['Fork the repo.', 'Add your webhook secret.'],
        });
      },
    );
  });

  test('Submit is disabled until the form is complete', ({
    given,
    when,
    then,
  }) => {
    givenDialogOpen(given);
    then('the submit button is disabled', () => {
      expect(
        screen.getByRole('button', { name: 'Submit for review' }),
      ).toBeDisabled();
    });
    whenFillComplete(when);
    then('the submit button is enabled', () => {
      expect(
        screen.getByRole('button', { name: 'Submit for review' }),
      ).toBeEnabled();
    });
  });

  test('Daily limit reached', ({ given, when, then, and }) => {
    givenDialogOpen(given);
    givenRejection(and);
    whenFillComplete(when);
    whenClickSubmit(and);
    thenErrorKeepsValues(then, and);
  });

  test('Server failure', ({ given, when, then, and }) => {
    givenDialogOpen(given);
    givenRejection(and);
    whenFillComplete(when);
    whenClickSubmit(and);
    thenErrorKeepsValues(then, and);
  });

  test('AI prompts are guided to put the prompt in the setup steps', ({
    given,
    when,
    then,
    and,
  }) => {
    givenDialogOpen(given);
    then('there is no separate prompt field', () => {
      expect(screen.queryByLabelText(/prompt/i)).not.toBeInTheDocument();
    });
    and('the setup steps hint asks for the prompt', () => {
      expect(
        screen.getByText(/include your prompt as its own step/i),
      ).toBeInTheDocument();
    });
    when(/^I choose the "(.*)" category$/, async (label) => {
      await chooseCategory(label);
    });
    then('the setup steps hint does not mention a prompt', () => {
      expect(
        screen.queryByText(/include your prompt as its own step/i),
      ).not.toBeInTheDocument();
    });
  });
  test('Enter starts the next setup step', ({ given, when, then }) => {
    givenDialogOpen(given);
    when('I type a step and press Enter', async () => {
      await user.type(screen.getByLabelText('Step 1'), 'Fork the repo.{enter}');
    });
    then('a second step is added and focused', () => {
      expect(screen.getByLabelText('Step 1')).toHaveValue('Fork the repo.');
      expect(screen.getByLabelText('Step 2')).toHaveFocus();
    });
  });

  test('A pasted multi-line prompt stays one step', ({ given, when, then }) => {
    givenDialogOpen(given);
    when('I paste a multi-line prompt into a step', async () => {
      await user.click(screen.getByLabelText('Step 1'));
      await user.paste('Read README.md first.\nThen grade each trade.');
    });
    then('the step holds the prompt on one line', () => {
      expect(screen.getByLabelText('Step 1')).toHaveValue(
        'Read README.md first. Then grade each trade.',
      );
      expect(screen.queryByLabelText('Step 2')).not.toBeInTheDocument();
    });
  });

  test('Steps can be added up to the limit and removed', ({
    given,
    when,
    then,
    and,
  }) => {
    givenDialogOpen(given);
    then('the only step cannot be removed', () => {
      expect(
        screen.getByRole('button', { name: 'Remove step 1' }),
      ).toBeDisabled();
    });
    when(/^I add steps until there are (\d+)$/, async (count) => {
      for (let i = 1; i < Number(count); i++) {
        await user.click(screen.getByRole('button', { name: 'Add step' }));
      }
    });
    then('no more steps can be added', () => {
      expect(screen.getByLabelText('Step 10')).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: 'Add step' }),
      ).not.toBeInTheDocument();
    });
    when('I remove step 3', async () => {
      await user.type(screen.getByLabelText('Step 4'), 'Fourth');
      await user.click(screen.getByRole('button', { name: 'Remove step 3' }));
    });
    and(/^there are (\d+) steps and the fourth step moved up$/, (count) => {
      expect(screen.getAllByLabelText(/^Step \d+$/)).toHaveLength(
        Number(count),
      );
      expect(screen.getByLabelText('Step 3')).toHaveValue('Fourth');
      expect(
        screen.getByRole('button', { name: 'Add step' }),
      ).toBeInTheDocument();
    });
  });
});
