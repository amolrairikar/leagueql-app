import { ArrowDown, ArrowUp, Repeat } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { Skeleton } from '@/components/ui/skeleton';
import SeasonSelect from '@/features/season_select/season-select';
import {
  type TransactionDraftPick,
  type TransactionItem,
  type TransactionPlayer,
  getTransactions,
} from '@/features/transactions/api-calls';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';

type TransactionsResult = Result<TransactionItem[]>;

const TYPE_LABELS: Record<string, string> = {
  trade: 'Trade',
  waiver: 'Waiver',
  free_agent: 'Free Agent',
  commissioner: 'Commissioner',
};

type TypeFilter = 'all' | 'trade' | 'waiver' | 'free_agent';

const TYPE_FILTERS: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'trade', label: 'Trades' },
  { value: 'waiver', label: 'Waivers' },
  { value: 'free_agent', label: 'Free Agents' },
];

function typeLabel(type: string): string {
  return TYPE_LABELS[type] ?? type;
}

function playerLabel(player: TransactionPlayer): string {
  const name = player.player_name ?? `Player ${player.player_id}`;
  return player.position ? `${name} (${player.position})` : name;
}

function pickLabel(pick: TransactionDraftPick): string {
  const base = `${pick.season} Round ${pick.round} pick`;
  // When the pick has already been used, show the player it became.
  return pick.player_name ? `${base} (${pick.player_name})` : base;
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

function TransactionCard({ txn }: { txn: TransactionItem }) {
  const date = new Date(txn.created).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  // In a trade, every drop is the other side's add, so showing both per team is
  // redundant — each team's card shows only what it received. Waivers and free
  // agents are a single roster's own add/drop, so both are shown there.
  const isTrade = txn.type === 'trade';

  return (
    <div className="bg-card border border-border/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.07em] text-foreground">
            <Repeat className="w-3.5 h-3.5 text-muted-foreground" />
            {typeLabel(txn.type)}
          </span>
          {txn.waiver_bid != null && txn.waiver_bid > 0 && (
            <span className="text-[11px] text-muted-foreground">
              ${txn.waiver_bid} FAAB
            </span>
          )}
        </div>
        <span className="text-[11px] text-muted-foreground">
          Week {txn.week} · {date}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {involvedRosterIds(txn).map((rosterId) => {
          const adds = txn.adds.filter((a) => a.roster_id === rosterId);
          const drops = isTrade
            ? []
            : txn.drops.filter((d) => d.roster_id === rosterId);
          const picksIn = txn.draft_picks.filter(
            (p) => p.to_roster_id === rosterId,
          );
          const picksOut = isTrade
            ? []
            : txn.draft_picks.filter((p) => p.from_roster_id === rosterId);
          return (
            <div
              key={rosterId}
              className="rounded-md border border-border/40 p-3"
            >
              <p className="text-[13px] font-medium text-foreground mb-1.5">
                {teamLabel(txn, rosterId)}
              </p>
              <ul className="flex flex-col gap-1">
                {adds.map((p) => (
                  <li
                    key={`add-${p.player_id}`}
                    className="flex items-center gap-1.5 text-[12px] text-emerald-600 dark:text-emerald-400"
                  >
                    <ArrowUp className="w-3 h-3 shrink-0" />
                    {playerLabel(p)}
                  </li>
                ))}
                {picksIn.map((p, i) => (
                  <li
                    key={`pickin-${i}`}
                    className="flex items-center gap-1.5 text-[12px] text-emerald-600 dark:text-emerald-400"
                  >
                    <ArrowUp className="w-3 h-3 shrink-0" />
                    {pickLabel(p)}
                  </li>
                ))}
                {drops.map((p) => (
                  <li
                    key={`drop-${p.player_id}`}
                    className="flex items-center gap-1.5 text-[12px] text-red-600 dark:text-red-400"
                  >
                    <ArrowDown className="w-3 h-3 shrink-0" />
                    {playerLabel(p)}
                  </li>
                ))}
                {picksOut.map((p, i) => (
                  <li
                    key={`pickout-${i}`}
                    className="flex items-center gap-1.5 text-[12px] text-red-600 dark:text-red-400"
                  >
                    <ArrowDown className="w-3 h-3 shrink-0" />
                    {pickLabel(p)}
                  </li>
                ))}
                {adds.length === 0 &&
                  drops.length === 0 &&
                  picksIn.length === 0 &&
                  picksOut.length === 0 && (
                    <li className="text-[12px] text-muted-foreground">
                      No moves
                    </li>
                  )}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TransactionsBody({
  promise,
  typeFilter,
}: {
  promise: Promise<TransactionsResult>;
  typeFilter: TypeFilter;
}) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">
        {result.error}
      </p>
    );
  }

  const transactions = [...result.data]
    .filter((t) => typeFilter === 'all' || t.type === typeFilter)
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
        <TransactionCard key={txn.transaction_id} txn={txn} />
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

export default function Transactions() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');

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

  return (
    <div className="flex flex-1 flex-col p-6 overflow-hidden">
      <div className="max-w-225 mx-auto w-full flex flex-1 flex-col min-h-0">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {seasons.length > 0 && (
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={setSelectedSeason}
            />
          )}
          <div className="flex items-center gap-1">
            {TYPE_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setTypeFilter(f.value)}
                className={`text-[12px] px-2.5 py-1 rounded-md border transition-colors cursor-pointer ${
                  typeFilter === f.value
                    ? 'bg-foreground text-background border-foreground'
                    : 'bg-card text-muted-foreground border-border/50 hover:text-foreground'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Transactions
        </p>

        {/* Only the list scrolls, so the season/type controls stay pinned and the
            page itself never grows past the viewport. */}
        <div className="flex-1 min-h-0 overflow-auto pb-2">
          <Suspense fallback={<SkeletonList />}>
            <TransactionsBody
              promise={transactionsPromise}
              typeFilter={typeFilter}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
