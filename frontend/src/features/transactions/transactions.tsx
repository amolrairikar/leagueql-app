import { Suspense, use, useMemo, useState } from 'react';

import SeasonSelect from '@/features/season_select/season-select';
import { getSeasonStandings } from '@/features/season_standings/api-calls';
import {
  buildRosterWeeklyPoints,
  buildWeeklyPlayerPoints,
  getSeasonMatchups,
  getTransactions,
} from '@/features/transactions/api-calls';
import { SkeletonList, TableSkeleton } from '@/features/transactions/skeletons';
import { SummaryTable } from '@/features/transactions/summary-table';
import { TopTransactions } from '@/features/transactions/top-transactions';
import { TransactionCard } from '@/features/transactions/transaction-card';
import { buildRosterExits } from '@/features/transactions/transaction-impact';
import { typeMeta } from '@/features/transactions/type-meta';
import {
  TYPE_FILTERS,
  type MatchupsResult,
  type StandingsResult,
  type TransactionsResult,
  type TypeFilter,
} from '@/features/transactions/types';
import { buildTransactionVisuals } from '@/features/transactions/visuals';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { latestSeason, seasonQuery } from '@/lib/season';
import { cn } from '@/lib/utils';

function TransactionsBody({
  promise,
  standingsPromise,
  matchupsPromise,
  typeFilter,
}: {
  promise: Promise<TransactionsResult>;
  standingsPromise: Promise<StandingsResult>;
  matchupsPromise: Promise<MatchupsResult>;
  typeFilter: TypeFilter;
}) {
  const result = use(promise);
  const standingsResult = use(standingsPromise);
  const matchupsResult = use(matchupsPromise);

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

  // Rest-of-season points for trades come from the season's matchup box scores. A missing or
  // failed matchups load degrades silently — trades render without the points additions.
  const weekly = matchupsResult.ok
    ? buildWeeklyPlayerPoints(matchupsResult.data)
    : null;
  // Built from the whole season (not the filtered wire) so a waiver/FA add's later drop or trade
  // away ends its points window whatever that later transaction's type.
  const exits = buildRosterExits(result.data);
  // Waiver / free-agent adds count only weeks in the acquiring roster's lineup.
  const rosterWeekly = matchupsResult.ok
    ? buildRosterWeeklyPoints(matchupsResult.data)
    : null;

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
        <TransactionCard
          key={txn.transaction_id}
          txn={txn}
          visuals={visuals}
          weekly={weekly}
          rosterWeekly={rosterWeekly}
          exits={exits}
        />
      ))}
    </div>
  );
}

/**
 * The Top transactions highlight. It ranks by rest-of-season points, so it renders only once the
 * season's matchup box scores have loaded; a failed/missing transactions or matchups load renders
 * nothing (the wire below surfaces any transactions error). Independent of the type filter.
 */
function TopTransactionsSection({
  promise,
  standingsPromise,
  matchupsPromise,
}: {
  promise: Promise<TransactionsResult>;
  standingsPromise: Promise<StandingsResult>;
  matchupsPromise: Promise<MatchupsResult>;
}) {
  const result = use(promise);
  const standingsResult = use(standingsPromise);
  const matchupsResult = use(matchupsPromise);

  if (!result.ok || !matchupsResult.ok) return null;

  return (
    <TopTransactions
      transactions={result.data}
      weekly={buildWeeklyPlayerPoints(matchupsResult.data)}
      rosterWeekly={buildRosterWeeklyPoints(matchupsResult.data)}
      visuals={buildTransactionVisuals(
        result.data,
        standingsResult.ok ? standingsResult.data : [],
      )}
    />
  );
}

export default function Transactions() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const [selectedSeason, setSelectedSeason] = useState(latestSeason(seasons));

  // Every platform (Sleeper, ESPN, Yahoo) produces trades, so the filter offers
  // Trades / Waivers / Free Agents and defaults to Trades.
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('trade');
  // Only ESPN shows the historical-transactions disclaimer.
  const isEspn = platform === 'ESPN';

  const transactionsPromise = useMemo(
    (): Promise<TransactionsResult> =>
      seasonQuery(
        Boolean(leagueId && selectedSeason),
        () => getTransactions(leagueId, platform, selectedSeason),
        'Failed to load transactions.',
      ),
    [leagueId, platform, selectedSeason],
  );

  // Standings supplies the avatar/color the summary table reuses (frontend/season-standings); a missing or failed
  // load is tolerated — the summary falls back to index-based colors and initials.
  const standingsPromise = useMemo(
    (): Promise<StandingsResult> =>
      seasonQuery(
        Boolean(leagueId && selectedSeason),
        () => getSeasonStandings(leagueId, platform, selectedSeason),
        'Failed to load standings.',
      ),
    [leagueId, platform, selectedSeason],
  );

  // Matchup box scores drive the rest-of-season points shown on trades. Fetched in parallel
  // with the transactions themselves; a missing/failed load is tolerated (trades render
  // without the points additions), so it never blocks or errors the wire.
  const matchupsPromise = useMemo(
    (): Promise<MatchupsResult> =>
      seasonQuery(
        Boolean(leagueId && selectedSeason),
        () => getSeasonMatchups(leagueId, platform, selectedSeason),
        'Failed to load matchups.',
      ),
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

        {isEspn && (
          <p className="text-[12px] text-muted-foreground mb-4">
            <span aria-hidden="true">*</span> The ESPN API does not return
            historical transactions, so only transactions from the 2026 fantasy
            season and onward are stored.
          </p>
        )}

        <Suspense fallback={null}>
          <TopTransactionsSection
            promise={transactionsPromise}
            standingsPromise={standingsPromise}
            matchupsPromise={matchupsPromise}
          />
        </Suspense>

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
              matchupsPromise={matchupsPromise}
              typeFilter={typeFilter}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
