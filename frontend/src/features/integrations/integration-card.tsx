import { CATEGORY_LABELS } from './constants';
import type { Integration, IntegrationCategory } from './types';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const BAR_HEIGHTS = [42, 68, 55, 80, 38, 72, 90, 60, 48, 76];

/**
 * Small decorative illustration of what an integration of this category looks
 * like (bars for dashboards, a grid for sheets, a chat message for bots, a query
 * for notebooks, a chat exchange for AI prompts). Purely presentational.
 */
export function CategoryPreview({
  category,
  className,
}: {
  category: IntegrationCategory;
  className?: string;
}) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'relative overflow-hidden border-b bg-muted px-4 py-3.5',
        className,
      )}
    >
      {category === 'dashboard' && (
        <div className="flex h-full items-end gap-1.5">
          {BAR_HEIGHTS.map((height, i) => (
            <span
              key={i}
              className={cn(
                'block flex-1 rounded-t-sm',
                i % 2 === 0 ? 'bg-chart-1' : 'bg-chart-2',
              )}
              style={{ height: `${height}%` }}
            />
          ))}
        </div>
      )}
      {category === 'spreadsheet' && (
        <div className="grid grid-cols-[1.6fr_repeat(3,1fr)] gap-px overflow-hidden rounded border bg-border font-mono text-[10px]">
          {[
            ['team', 'W-L', 'PF', 'rank'],
            ['Tyler', '9-3', '1,482', '1'],
            ['Priya', '8-4', '1,511', '2'],
            ['Marcus', '7-5', '1,397', '3'],
          ].map((row, r) =>
            row.map((cell) => (
              <span
                key={`${r}-${cell}`}
                className={cn(
                  'truncate px-1.5 py-0.5',
                  r === 0
                    ? 'bg-muted font-medium text-muted-foreground'
                    : 'bg-card',
                )}
              >
                {cell}
              </span>
            )),
          )}
        </div>
      )}
      {category === 'bot' && (
        <div className="flex gap-2 text-[11.5px]">
          <span className="size-6.5 shrink-0 rounded-full bg-chart-3" />
          <div className="min-w-0">
            <span className="font-semibold">LeagueBot</span>{' '}
            <span className="text-muted-foreground">Tue 9:00</span>
            <div className="mt-1 rounded-sm border-l-3 border-chart-2 bg-card px-2 py-1 text-muted-foreground">
              Week 4 blowout: 152.3 – 88.1
            </div>
            <div className="mt-1 rounded-sm border-l-3 border-chart-2 bg-card px-2 py-1 text-muted-foreground">
              Closest game: 0.6 pts
            </div>
          </div>
        </div>
      )}
      {category === 'notebook' && (
        <pre className="font-mono text-[11px] leading-relaxed text-muted-foreground">
          <span className="text-primary">SELECT</span> owner, avg(points){'\n'}
          <span className="text-primary">FROM</span> {"'*_matchups.json'"}
          {'\n'}
          <span className="text-primary">GROUP BY</span> owner;
        </pre>
      )}
      {category === 'ai_prompt' && (
        <div className="flex flex-col gap-1.5 text-[11.5px]">
          <span className="self-end rounded-xl rounded-br-sm bg-primary px-2.5 py-1.5 text-primary-foreground">
            Grade everyone&apos;s 2025 draft
          </span>
          <span className="self-start rounded-xl rounded-bl-sm border bg-card px-2.5 py-1.5">
            Priya: <strong>A−</strong>. Two top-12 WRs after round 6…
          </span>
        </div>
      )}
    </div>
  );
}

/** Two-letter avatar for an author handle. */
export function AuthorAvatar({ handle }: { handle: string }) {
  const initials = handle
    .replace(/[^a-z]/gi, '')
    .slice(0, 2)
    .toUpperCase();
  return (
    <span
      aria-hidden="true"
      className="grid size-5.5 shrink-0 place-items-center rounded-full bg-chart-3 text-[10px] font-semibold text-primary-foreground"
    >
      {initials || '?'}
    </span>
  );
}

/** Chip naming one export view an integration reads. */
export function ViewChip({ children }: { children: string }) {
  return (
    <span className="rounded bg-muted px-1.5 py-px font-mono text-[11px] text-muted-foreground">
      {children}
    </span>
  );
}

/** Clickable card for one integration in the browse grid. */
export function IntegrationCard({
  integration,
  onSelect,
}: {
  integration: Integration;
  onSelect: (integration: Integration) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(integration)}
      className="flex cursor-pointer flex-col overflow-hidden rounded-lg border bg-card text-left transition hover:-translate-y-px hover:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 motion-reduce:transition-none"
    >
      <CategoryPreview category={integration.category} className="h-30" />
      <div className="flex flex-1 flex-col gap-2 px-4 pt-3.5 pb-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-[15px] font-semibold">{integration.name}</h3>
          <Badge variant="secondary">
            {CATEGORY_LABELS[integration.category]}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <AuthorAvatar handle={integration.author_handle} />@
          {integration.author_handle}
        </div>
        <p className="text-[13px] text-muted-foreground">
          {integration.description}
        </p>
        <div className="mt-auto flex flex-wrap gap-1 pt-1">
          {integration.views.map((view) => (
            <ViewChip key={view}>{view}</ViewChip>
          ))}
        </div>
      </div>
    </button>
  );
}
