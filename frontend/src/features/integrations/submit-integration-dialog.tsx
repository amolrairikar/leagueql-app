import { Check } from 'lucide-react';
import { useState, type FormEvent } from 'react';

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
  authorHandle: string;
  category: IntegrationCategory;
  link: string;
  views: ExportView[];
  description: string;
  setupSteps: string;
  prompt: string;
}

const EMPTY_FORM: FormState = {
  name: '',
  authorHandle: '',
  category: 'ai_prompt',
  link: '',
  views: [],
  description: '',
  setupSteps: '',
  prompt: '',
};

const TEXTAREA_CLASS =
  'min-h-18 w-full rounded-md border border-input bg-transparent px-2.5 py-1.5 text-base shadow-xs outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm dark:bg-input/30';

function stepsFrom(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
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
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedIssue, setSubmittedIssue] = useState<number | null>(null);

  const steps = stepsFrom(form.setupSteps);
  const isPrompt = form.category === 'ai_prompt';
  const canSubmit =
    !loading &&
    form.name.trim() !== '' &&
    form.authorHandle.trim() !== '' &&
    form.link.trim() !== '' &&
    form.views.length > 0 &&
    form.description.trim() !== '' &&
    steps.length > 0 &&
    steps.length <= LIMITS.setupSteps;

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
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
      setForm(EMPTY_FORM);
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
      author_handle: form.authorHandle.trim(),
      category: form.category,
      link: form.link.trim(),
      views: form.views,
      description: form.description.trim(),
      setup_steps: steps,
      prompt: isPrompt && form.prompt.trim() ? form.prompt.trim() : null,
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
      <DialogContent className="max-h-[calc(100vh-3rem)] overflow-y-auto sm:max-w-140">
        <DialogHeader>
          <DialogTitle>Submit your integration</DialogTitle>
          <DialogDescription>
            Share something you built on a LeagueQL export. Every submission is
            reviewed before it&apos;s listed.
          </DialogDescription>
        </DialogHeader>

        {submittedIssue !== null ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <span className="grid size-10 place-items-center rounded-full bg-primary/10 text-primary">
              <Check className="size-5" />
            </span>
            <p className="font-semibold">Submitted for review</p>
            <p className="max-w-[40ch] text-sm text-muted-foreground">
              Thanks! It&apos;s in the review queue as #{submittedIssue} and
              will appear on this page once it&apos;s approved.
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
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-name">Name</Label>
                <Input
                  id="integration-name"
                  value={form.name}
                  maxLength={LIMITS.name}
                  onChange={(e) => update('name', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-author">Your handle</Label>
                <Input
                  id="integration-author"
                  value={form.authorHandle}
                  maxLength={LIMITS.authorHandle}
                  onChange={(e) => update('authorHandle', e.target.value)}
                />
              </div>
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

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="integration-steps">Setup steps</Label>
              <textarea
                id="integration-steps"
                className={TEXTAREA_CLASS}
                placeholder={'Export all seasons.\nUpload the ZIP to …'}
                value={form.setupSteps}
                onChange={(e) => update('setupSteps', e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                One step per line, up to {LIMITS.setupSteps}.
              </p>
            </div>

            {isPrompt && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="integration-prompt">Prompt (optional)</Label>
                <textarea
                  id="integration-prompt"
                  className={cn(TEXTAREA_CLASS, 'font-mono')}
                  value={form.prompt}
                  maxLength={LIMITS.prompt}
                  onChange={(e) => update('prompt', e.target.value)}
                />
              </div>
            )}

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
      </DialogContent>
    </Dialog>
  );
}
