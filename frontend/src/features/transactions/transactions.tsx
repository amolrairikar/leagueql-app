import {
  ArrowDown,
  ArrowLeftRight,
  ArrowUp,
  Gavel,
  type LucideIcon,
  Repeat,
  UserPlus,
} from 'lucide-react';
import { type ReactNode, Suspense, use, useMemo, useState } from 'react';

import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import SeasonSelect from '@/features/season_select/season-select';
import {
  type SeasonStandingsItem,
  getSeasonStandings,
} from '@/features/season_standings/api-calls';
import {
  type TransactionItem,
  type TransactionPlayer,
  type TransactionTeam,
  getTransactions,
} from '@/features/transactions/api-calls';
import { avatarColor } from '@/lib/color-constants';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';
import { cn } from '@/lib/utils';

type TransactionsResult = Result<TransactionItem[]>;

type StandingsResult = Result<SeasonStandingsItem[]>;

/**
 * Per-type presentation: label, icon, and the accent classes for the type chip. The commissioner
 * entry is a neutral fallback — it is never filterable, but a stray commissioner move still renders
 * a sensible chip.
 */
const TYPE_META: Record<
  string,
  { label: string; Icon: LucideIcon; chip: string }
> = {
  trade: {
    label: 'Trade',
    Icon: Repeat,
    chip: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
  },
  waiver: {
    label: 'Waiver',
    Icon: Gavel,
    chip: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  free_agent: {
    label: 'Free Agent',
    Icon: UserPlus,
    chip: 'bg-sky-500/10 text-sky-600 dark:text-sky-400',
  },
  commissioner: {
    label: 'Commissioner',
    Icon: Repeat,
    chip: 'bg-muted text-muted-foreground',
  },
};

function typeMeta(type: string) {
  return TYPE_META[type] ?? TYPE_META.commissioner;
}

type TypeFilter = 'trade' | 'waiver' | 'free_agent';

const TYPE_FILTERS: { value: TypeFilter; label: string }[] = [
  { value: 'trade', label: 'Trades' },
  { value: 'waiver', label: 'Waivers' },
  { value: 'free_agent', label: 'Free Agents' },
];

function playerLabel(player: TransactionPlayer): ReactNode {
  const name = player.player_name ?? `Player ${player.player_id}`;
  return (
    <span>
      {name}
      {player.position && (
        <span className="text-muted-foreground font-normal">
          {' '}
          {player.position}
        </span>
      )}
    </span>
  );
}

function teamLabel(txn: TransactionItem, rosterId: string | null): string {
  if (rosterId === null) return 'Unknown team';
  const team = txn.teams.find((t) => t.roster_id === rosterId);
  if (!team) return `Roster ${rosterId}`;
  // Prefer the display name, then the team name, ignoring null/empty values.
  return (
    [team.display_name, team.team_name].find((n) => n) ?? `Roster ${rosterId}`
  );
}

/** All roster_ids touched by a transaction, in the order teams are listed. */
function involvedRosterIds(txn: TransactionItem): string[] {
  const ids = new Set<string>();
  for (const team of txn.teams) ids.add(team.roster_id);
  for (const add of txn.adds) ids.add(add.roster_id);
  for (const drop of txn.drops) ids.add(drop.roster_id);
  return [...ids];
}

/** The type columns the summary table tracks (commissioner moves are excluded). */
type SummaryType = 'waiver' | 'free_agent' | 'trade';

interface OwnerSummaryRow {
  rosterId: string;
  ownerUsername: string;
  teamName: string;
  waiver: number;
  free_agent: number;
  trade: number;
  total: number;
}

/**
 * Per-owner activity for the season, counted per transaction: each waiver, free-agent, or
 * trade transaction adds 1 to the matching column for every owner it involves. Only owners
 * that appear in at least one transaction are included; rows are sorted by total descending,
 * then owner name ascending. Commissioner transactions are ignored.
 */
function buildOwnerSummary(transactions: TransactionItem[]): OwnerSummaryRow[] {
  // Resolve each roster's team from every transaction it appears in, so the row can show the
  // owner username and team name (matching the other tables, e.g. Season Standings).
  const teams = new Map<string, TransactionTeam>();
  for (const txn of transactions) {
    for (const team of txn.teams) teams.set(team.roster_id, team);
  }

  const rows = new Map<string, OwnerSummaryRow>();
  const rowFor = (rosterId: string): OwnerSummaryRow => {
    let row = rows.get(rosterId);
    if (!row) {
      const team = teams.get(rosterId);
      const ownerUsername =
        [team?.display_name, team?.team_name].find((n) => n) ??
        `Roster ${rosterId}`;
      row = {
        rosterId,
        ownerUsername,
        teamName: [team?.team_name].find((n) => n) ?? `Team ${ownerUsername}`,
        waiver: 0,
        free_agent: 0,
        trade: 0,
        total: 0,
      };
      rows.set(rosterId, row);
    }
    return row;
  };

  for (const txn of transactions) {
    if (
      txn.type !== 'waiver' &&
      txn.type !== 'free_agent' &&
      txn.type !== 'trade'
    ) {
      continue;
    }
    const type: SummaryType = txn.type;
    for (const rosterId of involvedRosterIds(txn)) {
      const row = rowFor(rosterId);
      row[type] += 1;
      row.total += 1;
    }
  }

  return [...rows.values()].sort(
    (a, b) =>
      b.total - a.total || a.ownerUsername.localeCompare(b.ownerUsername),
  );
}

/** A single add (green ↑) or drop (red ↓) row inside a team panel. */
function MoveRow({
  direction,
  children,
}: {
  direction: 'add' | 'drop';
  children: ReactNode;
}) {
  const Icon = direction === 'add' ? ArrowUp : ArrowDown;
  return (
    <li
      className={cn(
        'flex items-center gap-1.5 text-[12px]',
        direction === 'add'
          ? 'text-emerald-600 dark:text-emerald-400'
          : 'text-red-600 dark:text-red-400',
      )}
    >
      <Icon className="w-3 h-3 shrink-0" />
      {children}
    </li>
  );
}

/** One team's panel within a transaction card: its avatar, name, and the moves it received. */
function TeamPanel({
  txn,
  rosterId,
  isTrade,
  visual,
}: {
  txn: TransactionItem;
  rosterId: string;
  isTrade: boolean;
  visual: OwnerVisual | undefined;
}) {
  const adds = txn.adds.filter((a) => a.roster_id === rosterId);
  // In a trade, every drop is the other side's add, so showing both per team is
  // redundant — each team's panel shows only what it received. Waivers and free
  // agents are a single roster's own add/drop, so both are shown there.
  const drops = isTrade
    ? []
    : txn.drops.filter((d) => d.roster_id === rosterId);
  const picksIn = txn.draft_picks.filter((p) => p.to_roster_id === rosterId);
  const picksOut = isTrade
    ? []
    : txn.draft_picks.filter((p) => p.from_roster_id === rosterId);

  const team = txn.teams.find((t) => t.roster_id === rosterId);
  const teamName =
    [team?.team_name, team?.display_name].find((n) => n) ??
    `Roster ${rosterId}`;
  const ownerUsername =
    [team?.display_name, team?.team_name].find((n) => n) ??
    `Roster ${rosterId}`;
  const empty =
    adds.length === 0 &&
    drops.length === 0 &&
    picksIn.length === 0 &&
    picksOut.length === 0;

  return (
    <div className="flex-1 min-w-0 rounded-lg border border-border/50 bg-muted/40 p-3">
      <div className="flex items-center gap-2 mb-2">
        <TeamAvatar
          teamLogo={visual?.teamLogo ?? null}
          teamName={teamName}
          ownerUsername={ownerUsername}
          color={avatarColor(visual?.colorIndex ?? 0)}
        />
        <span className="text-[13px] font-semibold text-foreground truncate">
          {teamLabel(txn, rosterId)}
        </span>
      </div>
      <ul className="flex flex-col gap-1">
        {adds.map((p) => (
          <MoveRow key={`add-${p.player_id}`} direction="add">
            {playerLabel(p)}
          </MoveRow>
        ))}
        {picksIn.map((p, i) => (
          <MoveRow key={`pickin-${i}`} direction="add">
            {p.season} Round {p.round} pick
          </MoveRow>
        ))}
        {drops.map((p) => (
          <MoveRow key={`drop-${p.player_id}`} direction="drop">
            {playerLabel(p)}
          </MoveRow>
        ))}
        {picksOut.map((p, i) => (
          <MoveRow key={`pickout-${i}`} direction="drop">
            {p.season} Round {p.round} pick
          </MoveRow>
        ))}
        {empty && (
          <li className="text-[12px] text-muted-foreground">No moves</li>
        )}
      </ul>
    </div>
  );
}

function TransactionCard({
  txn,
  visuals,
}: {
  txn: TransactionItem;
  visuals: Map<string, OwnerVisual>;
}) {
  const date = new Date(txn.created).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  const meta = typeMeta(txn.type);
  const isTrade = txn.type === 'trade';
  const rosterIds = involvedRosterIds(txn);
  const panel = (rosterId: string) => (
    <TeamPanel
      key={rosterId}
      txn={txn}
      rosterId={rosterId}
      isTrade={isTrade}
      visual={visuals.get(rosterId)}
    />
  );

  return (
    <div className="bg-card border border-border/50 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-3">
        <span
          className={cn(
            'inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full',
            meta.chip,
          )}
        >
          <meta.Icon className="w-3 h-3" />
          {meta.label}
        </span>
        <div className="flex items-center gap-2">
          {txn.waiver_bid != null && txn.waiver_bid > 0 && (
            <span className="inline-flex items-center text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
              ${txn.waiver_bid} FAAB
            </span>
          )}
          <span className="text-[11px] text-muted-foreground whitespace-nowrap">
            Week {txn.week} · {date}
          </span>
        </div>
      </div>

      {isTrade && rosterIds.length === 2 ? (
        <div className="flex flex-col sm:flex-row sm:items-stretch gap-2">
          {panel(rosterIds[0])}
          <div className="hidden sm:flex items-center justify-center shrink-0 px-1 text-muted-foreground">
            <ArrowLeftRight className="w-4 h-4" />
          </div>
          {panel(rosterIds[1])}
        </div>
      ) : (
        <div
          className={cn(
            'grid grid-cols-1 gap-2',
            rosterIds.length > 1 && 'sm:grid-cols-2',
          )}
        >
          {rosterIds.map(panel)}
        </div>
      )}
    </div>
  );
}

interface OwnerVisual {
  /** Index into the standings order, so `avatarColor(index)` matches the standings page. */
  colorIndex: number;
  teamLogo: string;
}

/**
 * Maps each roster_id to the avatar logo and color *index* used on the Season Standings page
 * (frontend/season-standings), so the summary table shows the same avatar/color per owner. Standings keys on
 * team_id, which is the roster_id for Sleeper (the only platform with transactions), and its
 * color is positional — `avatarColor(index)` over the API's returned order — so the index is
 * captured here rather than the resolved color.
 */
function buildStandingsVisuals(
  standings: SeasonStandingsItem[],
): Map<string, OwnerVisual> {
  return new Map(
    standings.map((s, i): [string, OwnerVisual] => [
      s.team_id,
      { colorIndex: i, teamLogo: s.team_logo },
    ]),
  );
}

/**
 * Avatar visuals for the transaction cards. Every roster that appears in a transaction gets a
 * color, so a card can render an avatar even when standings is missing: rosters are seeded in
 * first-appearance order, then Season Standings visuals (logo + positional color) are overlaid so
 * a roster present in standings matches its Season Standings / summary-table avatar exactly.
 */
function buildTransactionVisuals(
  transactions: TransactionItem[],
  standings: SeasonStandingsItem[],
): Map<string, OwnerVisual> {
  const visuals = new Map<string, OwnerVisual>();
  let i = 0;
  for (const txn of transactions) {
    for (const rosterId of involvedRosterIds(txn)) {
      if (!visuals.has(rosterId)) {
        visuals.set(rosterId, { colorIndex: i++, teamLogo: '' });
      }
    }
  }
  standings.forEach((s, idx) =>
    visuals.set(s.team_id, { colorIndex: idx, teamLogo: s.team_logo }),
  );
  return visuals;
}

function SummaryTable({
  promise,
  standingsPromise,
}: {
  promise: Promise<TransactionsResult>;
  standingsPromise: Promise<StandingsResult>;
}) {
  const result = use(promise);
  const standingsResult = use(standingsPromise);

  // The wire below renders the error / empty state, so the table stays out of the way.
  if (!result.ok) return null;
  const rows = buildOwnerSummary(result.data);
  if (rows.length === 0) return null;

  // Reuse the Season Standings avatar/color when standings is available; fall back to the
  // row's own index + initials when it isn't (e.g. a season with no standings yet, or a
  // roster not present in standings).
  const visuals = standingsResult.ok
    ? buildStandingsVisuals(standingsResult.data)
    : new Map<string, OwnerVisual>();
  const maxTotal = Math.max(...rows.map((r) => r.total), 1);

  const headCell =
    'text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted';

  return (
    <div className="bg-card border border-border/50 rounded-xl overflow-hidden shadow-sm">
      <div className="max-h-[70vh] overflow-auto">
        <table
          className="w-full border-collapse text-[13px]"
          style={{ tableLayout: 'fixed', minWidth: '480px' }}
        >
          <thead className="sticky top-0 z-20">
            <tr>
              <th
                className={`${headCell} text-left sticky left-0 z-10`}
                style={{ width: '40%' }}
              >
                Owner
              </th>
              <th className={`${headCell} text-right`}>Waivers</th>
              <th className={`${headCell} text-right`}>Free Agents</th>
              <th className={`${headCell} text-right`}>Trades</th>
              <th className={`${headCell} text-right`}>Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const visual = visuals.get(row.rosterId);
              return (
                <tr
                  key={row.rosterId}
                  className="border-b border-border/50 last:border-0 bg-card"
                >
                  <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
                    <div className="flex items-center gap-2">
                      <TeamAvatar
                        teamLogo={visual?.teamLogo ?? null}
                        teamName={row.teamName}
                        ownerUsername={row.ownerUsername}
                        color={avatarColor(visual?.colorIndex ?? i)}
                      />
                      <div className="flex flex-col">
                        <span className="text-[13px] font-medium text-foreground">
                          {row.ownerUsername}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          {row.teamName}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.waiver}
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.free_agent}
                  </td>
                  <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                    {row.trade}
                  </td>
                  <td className="px-3.5 py-2.5 text-right">
                    <span className="inline-flex items-center justify-end gap-2">
                      <span className="hidden sm:block h-1.5 w-12 rounded-full bg-muted overflow-hidden">
                        <span
                          className="block h-full rounded-full bg-primary"
                          style={{
                            width: `${Math.round((row.total / maxTotal) * 100)}%`,
                          }}
                        />
                      </span>
                      <span className="font-semibold text-foreground tabular-nums">
                        {row.total}
                      </span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TransactionsBody({
  promise,
  standingsPromise,
  typeFilter,
}: {
  promise: Promise<TransactionsResult>;
  standingsPromise: Promise<StandingsResult>;
  typeFilter: TypeFilter;
}) {
  const result = use(promise);
  const standingsResult = use(standingsPromise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">
        {result.error}
      </p>
    );
  }

  // Card avatars reuse the Season Standings logo/color when available (matching the summary
  // table), falling back to an appearance-order color + initials otherwise.
  const visuals = buildTransactionVisuals(
    result.data,
    standingsResult.ok ? standingsResult.data : [],
  );

  const transactions = [...result.data]
    .filter((t) => t.type === typeFilter)
    .sort((a, b) => b.created - a.created);

  if (transactions.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        No transactions for this season.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {transactions.map((txn) => (
        <TransactionCard key={txn.transaction_id} txn={txn} visuals={visuals} />
      ))}
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-28 w-full rounded-lg" />
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-1.5">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-9 w-full rounded-md" />
      ))}
    </div>
  );
}

export default function Transactions() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('trade');

  const transactionsPromise = useMemo(
    (): Promise<TransactionsResult> =>
      leagueId && selectedSeason
        ? toResult(
            getTransactions(leagueId, platform, selectedSeason).then(
              (res) => res.data,
            ),
            'Failed to load transactions.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  // Standings supplies the avatar/color the summary table reuses (frontend/season-standings); a missing or failed
  // load is tolerated — the summary falls back to index-based colors and initials.
  const standingsPromise = useMemo(
    (): Promise<StandingsResult> =>
      leagueId && selectedSeason
        ? toResult(
            getSeasonStandings(leagueId, platform, selectedSeason).then(
              (res) => res.data,
            ),
            'Failed to load standings.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {seasons.length > 0 && (
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={setSelectedSeason}
            />
          )}
        </div>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Summary
        </p>
        <div className="mb-4">
          <Suspense fallback={<TableSkeleton />}>
            <SummaryTable
              promise={transactionsPromise}
              standingsPromise={standingsPromise}
            />
          </Suspense>
        </div>

        <div className="inline-flex items-center gap-0.5 p-0.5 mb-4 rounded-lg bg-muted border border-border/60">
          {TYPE_FILTERS.map((f) => {
            const active = typeFilter === f.value;
            const { Icon } = typeMeta(f.value);
            return (
              <button
                key={f.value}
                type="button"
                aria-pressed={active}
                onClick={() => setTypeFilter(f.value)}
                className={cn(
                  'inline-flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-md transition-colors cursor-pointer',
                  active
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {f.label}
              </button>
            );
          })}
        </div>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Transactions
        </p>

        {/* The wire scrolls in its own bounded container so a long season can't make
            the page infinitely tall; the outer overflow-auto is a safety net so the
            section stays reachable on short viewports. */}
        <div className="max-h-[70vh] overflow-y-auto pb-2">
          <Suspense fallback={<SkeletonList />}>
            <TransactionsBody
              promise={transactionsPromise}
              standingsPromise={standingsPromise}
              typeFilter={typeFilter}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
