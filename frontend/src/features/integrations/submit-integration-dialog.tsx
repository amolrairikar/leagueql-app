import { Check, Plus, X } from 'lucide-react';
import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react';

import { submitIntegration } from './api-calls';
import { CATEGORIES, CATEGORY_LABELS, EXPORT_VIEWS, LIMITS } from './constants';
import type {
  ExportView,
  IntegrationCategory,
  IntegrationSubmission,
} from './types';

import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ApiError } from '@/lib/api-client';
import { ErrorAlert } from '@/lib/error-alert';
import { cn } from '@/lib/utils';

const SUBMIT_FALLBACK =
  "Couldn't submit right now. Try again in a few minutes.";
const VALIDATION_MESSAGE =
  'Some fields are invalid. Check the link is an https:// URL and try again.';

interface FormState {
  name: string;
  category: IntegrationCategory;
  link: string;
  views: ExportView[];
  description: string;
  setupSteps: SetupStepRow[];
}

/** One row of the step builder; `id` keeps React keys stable across removals. */
interface SetupStepRow {
  id: number;
  text: string;
}

let nextStepId = 0;

function newStep(): SetupStepRow {
  nextStepId += 1;
  return { id: nextStepId, text: '' };
}

function emptyForm(): FormState {
  return {
    name: '',
    category: 'ai_prompt',
    link: '',
    views: [],
    description: '',
    setupSteps: [newStep()],
  };
}

/** Show a step's character counter once it is this close to the limit. */
const STEP_COUNTER_THRESHOLD = LIMITS.setupStep - 100;

const TEXTAREA_CLASS =
  'min-h-18 w-full rounded-md border border-input bg-transparent px-2.5 py-1.5 text-base shadow-xs outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm dark:bg-input/30';

/** Steps are single-line: a pasted multi-line prompt is joined with spaces. */
function singleLine(text: string): string {
  return text.replace(/\s*\r?\n\s*/g, ' ');
}

function stepPlaceholder(index: number, isPrompt: boolean): string {
  if (index === 0) return 'Export your league from LeagueQL.';
  if (index === 1 && isPrompt) return 'Paste this prompt: …';
  return '';
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 422) return VALIDATION_MESSAGE;
    if (err.status >= 400 && err.status < 500) return err.message;
  }
  return SUBMIT_FALLBACK;
}

/**
 * Submit an integration for maintainer review (frontend/integrations). The
 * backend opens a GitHub issue; it is listed on the page once approved.
 */
export function SubmitIntegrationDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [form, setForm] = useState<FormState>(emptyForm);
  const stepRefs = useRef(new Map<number, HTMLTextAreaElement>());
  // A step added via Enter / "Add step" takes focus as soon as it mounts.
  const focusOnMountId = useRef<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedIssue, setSubmittedIssue] = useState<number | null>(null);

  const steps = form.setupSteps.map((step) => step.text.trim()).filter(Boolean);
  const canAddStep = form.setupSteps.length < LIMITS.setupSteps;
  const isPrompt = form.category === 'ai_prompt';
  const canSubmit =
    !loading &&
    form.name.trim() !== '' &&
    form.link.trim() !== '' &&
    form.views.length > 0 &&
    form.description.trim() !== '' &&
    steps.length > 0 &&
    steps.length <= LIMITS.setupSteps;

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateStep(id: number, text: string) {
    update(
      'setupSteps',
      form.setupSteps.map((step) =>
        step.id === id ? { ...step, text: singleLine(text) } : step,
      ),
    );
  }

  function addStepAfter(index: number) {
    if (!canAddStep) return;
    const step = newStep();
    focusOnMountId.current = step.id;
    update('setupSteps', form.setupSteps.toSpliced(index + 1, 0, step));
  }

  function removeStep(index: number) {
    const remaining = form.setupSteps.toSpliced(index, 1);
    update('setupSteps', remaining);
    stepRefs.current.get(remaining[Math.max(0, index - 1)].id)?.focus();
  }

  function handleStepKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>,
    index: number,
  ) {
    if (event.key !== 'Enter' || event.nativeEvent.isComposing) return;
    // Enter starts the next step instead of a line break.
    event.preventDefault();
    addStepAfter(index);
  }

  function toggleView(view: ExportView) {
    update(
      'views',
      form.views.includes(view)
        ? form.views.filter((v) => v !== view)
        : [...form.views, view],
    );
  }

  function handleOpenChange(next: boolean) {
    // A finished submission starts fresh next time; an unsent draft is kept.
    if (!next && submittedIssue !== null) {
      setForm(emptyForm());
      setSubmittedIssue(null);
    }
    if (!next) setError(null);
    onOpenChange(next);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    const submission: IntegrationSubmission = {
      name: form.name.trim(),
      category: form.category,
      link: form.link.trim(),
      views: form.views,
      description: form.description.trim(),
      setup_steps: steps,
    };
    setLoading(true);
    setError(null);
    try {
      setSubmittedIssue(await submitIntegration(submission));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 p-0 sm:max-w-140">
        <DialogHeader className="p-6 pr-12 pb-4">
          <DialogTitle>Submit your integration</DialogTitle>
          <DialogDescription>
            Share something you built on a LeagueQL export. Every submission is
            reviewed before it&apos;s listed.
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-col gap-6 overflow-y-auto overscroll-contain px-6 pb-6">
          {submittedIssue !== null ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <span className="grid size-10 place-items-center rounded-full bg-primary/10 text-primary">
                <Check className="size-5" />
              </span>
              <p className="font-semibold">Submitted for review</p>
              <p className="max-w-[40ch] text-sm text-muted-foreground">
                Thanks! We have received your submission and will feature your
                integration on this page if it&apos;s approved.
              </p>
              <Button
                className="mt-2 cursor-pointer"
                onClick={() => handleOpenChange(false)}
              >
                Done
              </Button>
            </div>
          ) : (
            <form
              onSubmit={(event) => void handleSubmit(event)}
              className="flex flex-col gap-4"
            >
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-name">Integration Name</Label>
                <Input
                  id="integration-name"
                  value={form.name}
                  maxLength={LIMITS.name}
                  onChange={(e) => update('name', e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-category">Category</Label>
                <Select
                  value={form.category}
                  onValueChange={(value) =>
                    update('category', value as IntegrationCategory)
                  }
                >
                  <SelectTrigger
                    id="integration-category"
                    className="w-full cursor-pointer"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((category) => (
                      <SelectItem
                        key={category}
                        value={category}
                        className="cursor-pointer"
                      >
                        {CATEGORY_LABELS[category]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-link">Link</Label>
                <Input
                  id="integration-link"
                  type="url"
                  placeholder="https://"
                  value={form.link}
                  maxLength={LIMITS.link}
                  onChange={(e) => update('link', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  A repo, template or shared prompt that other leagues can open.
                </p>
              </div>

              <fieldset className="flex flex-col gap-1.5">
                <legend className="mb-1.5 text-sm font-medium">
                  Views it reads
                </legend>
                <div className="flex flex-wrap gap-1.5">
                  {EXPORT_VIEWS.map((view) => (
                    <label
                      key={view}
                      className={cn(
                        'inline-flex cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-xs',
                        form.views.includes(view) && 'border-primary',
                      )}
                    >
                      <input
                        type="checkbox"
                        className="size-3.5 cursor-pointer accent-primary"
                        checked={form.views.includes(view)}
                        onChange={() => toggleView(view)}
                      />
                      {view}
                    </label>
                  ))}
                </div>
              </fieldset>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-description">What it does</Label>
                <textarea
                  id="integration-description"
                  className={TEXTAREA_CLASS}
                  value={form.description}
                  maxLength={LIMITS.description}
                  onChange={(e) => update('description', e.target.value)}
                />
              </div>

              <fieldset className="flex flex-col gap-1.5">
                <legend className="mb-1.5 text-sm font-medium">
                  Setup steps
                </legend>
                <ol className="flex flex-col gap-2">
                  {form.setupSteps.map((step, index) => (
                    <li key={step.id} className="flex items-start gap-2">
                      <span
                        aria-hidden="true"
                        className="mt-1.5 grid size-5 shrink-0 place-items-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground"
                      >
                        {index + 1}
                      </span>
                      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <textarea
                          ref={(el) => {
                            if (!el) {
                              stepRefs.current.delete(step.id);
                              return;
                            }
                            stepRefs.current.set(step.id, el);
                            if (focusOnMountId.current === step.id) {
                              focusOnMountId.current = null;
                              el.focus();
                            }
                          }}
                          aria-label={`Step ${index + 1}`}
                          rows={1}
                          className={cn(
                            TEXTAREA_CLASS,
                            'min-h-0 resize-none field-sizing-content',
                          )}
                          placeholder={stepPlaceholder(index, isPrompt)}
                          value={step.text}
                          maxLength={LIMITS.setupStep}
                          onChange={(e) => updateStep(step.id, e.target.value)}
                          onKeyDown={(e) => handleStepKeyDown(e, index)}
                        />
                        {step.text.length >= STEP_COUNTER_THRESHOLD && (
                          <span className="self-end text-[11px] text-muted-foreground tabular-nums">
                            {step.text.length}/{LIMITS.setupStep}
                          </span>
                        )}
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="shrink-0 cursor-pointer text-muted-foreground"
                        aria-label={`Remove step ${index + 1}`}
                        disabled={form.setupSteps.length === 1}
                        onClick={() => removeStep(index)}
                      >
                        <X />
                      </Button>
                    </li>
                  ))}
                </ol>
                {canAddStep && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="self-start cursor-pointer"
                    onClick={() => addStepAfter(form.setupSteps.length - 1)}
                  >
                    <Plus />
                    Add step
                  </Button>
                )}
                <p className="text-xs text-muted-foreground">
                  Up to {LIMITS.setupSteps} steps. Press Enter to start the next
                  one.
                  {isPrompt &&
                    ' Include your prompt as its own step, e.g. "Paste this prompt: …".'}
                </p>
              </fieldset>

              <p className="rounded-md bg-muted px-3 py-2.5 text-xs text-muted-foreground">
                Don&apos;t include your league&apos;s data, cookies or tokens.
                Integrations should work with anyone&apos;s export.
              </p>

              {error && <ErrorAlert message={error} />}

              <DialogFooter>
                <Button
                  type="button"
                  variant="ghost"
                  className="cursor-pointer"
                  onClick={() => handleOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="cursor-pointer"
                  disabled={!canSubmit}
                >
                  {loading && <Spinner />}
                  Submit for review
                </Button>
              </DialogFooter>
            </form>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
