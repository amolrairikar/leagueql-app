import { Plus, Search } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { listIntegrations } from './api-calls';
import {
  CATEGORIES,
  CATEGORY_CHIP_LABELS,
  CATEGORY_LABELS,
  HOW_IT_WORKS,
} from './constants';
import {
  AuthorAvatar,
  CategoryPreview,
  IntegrationCard,
  ViewChip,
} from './integration-card';
import { IntegrationDetailDialog } from './integration-detail-dialog';
import { SubmitIntegrationDialog } from './submit-integration-dialog';
import type { Integration, IntegrationCategory } from './types';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ErrorAlert } from '@/lib/error-alert';
import { toResult, type Result } from '@/lib/result';
import { cn } from '@/lib/utils';

const LIST_FALLBACK =
  "Couldn't load integrations right now. Try again in a few minutes.";

/**
 * Community integrations built on the league export (frontend/integrations):
 * how it works, the featured integration, and a filterable grid of every
 * maintainer-approved integration, plus the submit-for-review dialog.
 */
export default function IntegrationsPage() {
  const [selected, setSelected] = useState<Integration | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);

  const listPromise = useMemo(
    () => toResult(listIntegrations(), LIST_FALLBACK),
    [],
  );

  return (
    <div className="flex flex-1 flex-col overflow-auto p-6">
      <div className="mx-auto flex w-full max-w-295 flex-col gap-8">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-balance">
              Integrations
            </h1>
            <p className="mt-1.5 max-w-[62ch] text-sm text-muted-foreground">
              Bots, dashboards, spreadsheets and AI prompts that league managers
              built on their LeagueQL exports. Pick one, export your seasons,
              and plug your own league in.
            </p>
          </div>
          <Button onClick={() => setSubmitOpen(true)}>
            <Plus />
            Submit your integration
          </Button>
        </header>

        <HowItWorks />

        <Suspense
          fallback={
            <p className="py-12 text-center text-muted-foreground">
              Loading integrations...
            </p>
          }
        >
          <IntegrationsContent
            promise={listPromise}
            onSelect={setSelected}
            onSubmit={() => setSubmitOpen(true)}
          />
        </Suspense>
      </div>

      <IntegrationDetailDialog
        integration={selected}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      />
      <SubmitIntegrationDialog open={submitOpen} onOpenChange={setSubmitOpen} />
    </div>
  );
}

function HowItWorks() {
  return (
    <section
      aria-label="How it works"
      className="grid rounded-xl border bg-card md:grid-cols-3"
    >
      {HOW_IT_WORKS.map((step, i) => (
        <div
          key={step.title}
          className={cn(
            'grid grid-cols-[auto_1fr] items-start gap-x-3 gap-y-1 px-5 py-4.5',
            i > 0 && 'border-t md:border-t-0 md:border-l',
          )}
        >
          <span className="row-span-2 grid size-6.5 place-items-center rounded-full bg-muted font-mono text-xs">
            {i + 1}
          </span>
          <h2 className="text-sm font-semibold">{step.title}</h2>
          <p className="text-[13px] text-muted-foreground">{step.body}</p>
        </div>
      ))}
    </section>
  );
}

function IntegrationsContent({
  promise,
  onSelect,
  onSubmit,
}: {
  promise: Promise<Result<Integration[]>>;
  onSelect: (integration: Integration) => void;
  onSubmit: () => void;
}) {
  const result = use(promise);
  if (!result.ok) return <ErrorAlert message={result.error} />;

  const items = result.data;
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-4 py-10 text-center text-muted-foreground">
        <p>No integrations yet. Be the first to submit one.</p>
        <Button variant="outline" size="sm" onClick={onSubmit}>
          Submit your integration
        </Button>
      </div>
    );
  }

  const featured = items.find((item) => item.featured);
  return (
    <>
      {featured && <FeaturedCard integration={featured} onSelect={onSelect} />}
      <BrowseIntegrations items={items} onSelect={onSelect} />
    </>
  );
}

function FeaturedCard({
  integration,
  onSelect,
}: {
  integration: Integration;
  onSelect: (integration: Integration) => void;
}) {
  return (
    <section
      aria-label="Featured integration"
      className="grid overflow-hidden rounded-xl border bg-card shadow-sm md:grid-cols-[1.1fr_1fr]"
    >
      <div className="flex flex-col gap-3 p-6">
        <p className="text-[11.5px] font-semibold tracking-wider text-primary uppercase">
          Featured
        </p>
        <h2 className="text-[22px] font-semibold tracking-tight">
          {integration.name}
        </h2>
        <p className="max-w-[58ch] text-muted-foreground">
          {integration.description}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary">
            {CATEGORY_LABELS[integration.category]}
          </Badge>
          {integration.views.map((view) => (
            <ViewChip key={view}>{view}</ViewChip>
          ))}
        </div>
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <AuthorAvatar handle={integration.author_handle} />@
          {integration.author_handle}
        </div>
        <div className="mt-auto pt-1">
          <Button onClick={() => onSelect(integration)}>View setup</Button>
        </div>
      </div>
      <CategoryPreview
        category={integration.category}
        className="flex min-h-40 flex-col justify-center border-t border-b-0 p-5 md:border-t-0 md:border-l"
      />
    </section>
  );
}

function BrowseIntegrations({
  items,
  onSelect,
}: {
  items: Integration[];
  onSelect: (integration: Integration) => void;
}) {
  const [category, setCategory] = useState<IntegrationCategory | 'all'>('all');
  const [query, setQuery] = useState('');

  const q = query.trim().toLowerCase();
  const visible = items.filter(
    (item) =>
      (category === 'all' || item.category === category) &&
      (!q ||
        [item.name, item.description, ...item.views].some((text) =>
          text.toLowerCase().includes(q),
        )),
  );

  const chips: { value: IntegrationCategory | 'all'; label: string }[] = [
    { value: 'all', label: 'All' },
    ...CATEGORIES.map((c) => ({ value: c, label: CATEGORY_CHIP_LABELS[c] })),
  ];

  return (
    <section aria-label="Browse integrations" className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">Browse integrations</h2>
        <span className="text-[13px] text-muted-foreground tabular-nums">
          {visible.length} of {items.length} integrations
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        <div
          role="group"
          aria-label="Filter by category"
          className="flex flex-wrap gap-1.5"
        >
          {chips.map((chip) => {
            const count =
              chip.value === 'all'
                ? items.length
                : items.filter((item) => item.category === chip.value).length;
            const active = category === chip.value;
            return (
              <button
                key={chip.value}
                type="button"
                aria-pressed={active}
                onClick={() => setCategory(chip.value)}
                className={cn(
                  'h-7.5 rounded-full border px-3 text-[13px] transition-colors',
                  active
                    ? 'border-foreground bg-foreground text-background'
                    : 'bg-card hover:bg-muted',
                )}
              >
                {chip.label}
                <span className="ml-1 tabular-nums opacity-60">{count}</span>
              </button>
            );
          })}
        </div>
        <label className="relative w-full sm:ml-auto sm:w-65">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            aria-label="Search integrations"
            placeholder="Search by name or view…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-8"
          />
        </label>
      </div>
      {visible.length > 0 ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
          {visible.map((item) => (
            <IntegrationCard
              key={item.issue_number}
              integration={item}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : (
        <p className="rounded-lg border border-dashed px-4 py-10 text-center text-muted-foreground">
          No integrations match. Try another category or search.
        </p>
      )}
    </section>
  );
}
