import { use } from 'react';

import { type AllTimeStandingsData } from '@/features/home_page/all-time-data';
import { AllTimeStandingsTable } from '@/features/home_page/all-time-standings';
import { StandingsChart } from '@/features/home_page/standings-chart';
import {
  computeChampions,
  computeTotalGames,
  computeTotalMembers,
  type ChampionItem,
  type StatItem,
} from '@/features/home_page/summary-stats';
import { ErrorAlert } from '@/lib/error-alert';
import { type Result } from '@/lib/result';

export function ChampionsGrid({ champions }: { champions: ChampionItem[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-6">
      {champions.map((champ) => (
        <div
          key={champ.season}
          className={`bg-card border border-border/50 rounded-lg p-2.5 flex flex-col gap-0.5 ${
            champ.highlight ? 'border-primary bg-primary/5' : ''
          }`}
        >
          <div className="text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
            {champ.season}
          </div>
          <div className="text-[13px] font-medium text-foreground leading-tight">
            {champ.name}
          </div>
          <div className="text-[11px] text-muted-foreground">{champ.owner}</div>
          <div className="text-[11px] text-muted-foreground">
            {champ.record} · {champ.pfGame} PF/G
          </div>
        </div>
      ))}
    </div>
  );
}

export function StatsWithTotalGames({
  stats,
  totalGames,
  champions,
  totalMembers,
}: {
  stats: StatItem[];
  totalGames: number;
  champions: ChampionItem[];
  totalMembers: number;
}) {
  const uniqueChampions = new Set(
    champions.filter((c) => c.owner !== '—').map((c) => c.owner),
  ).size;

  const displayStats = [
    ...stats.slice(0, 1),
    {
      label: 'Total matchups',
      value: totalGames.toLocaleString(),
    },
    {
      label: 'Total members',
      value: String(totalMembers),
    },
    {
      label: 'Unique champions',
      value: String(uniqueChampions),
    },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
      {displayStats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card border border-border/50 rounded-lg p-3 text-center"
        >
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            {stat.label}
          </div>
          <div className="text-[22px] font-medium text-foreground leading-none">
            {stat.value}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {'sub' in stat ? stat.sub : ' '}
          </div>
        </div>
      ))}
    </div>
  );
}

// Consumes the single league-data call. All summary sections derive from this
// one request, so on failure we surface a single inline error in place of the
// (otherwise empty) tables and chart rather than silently rendering blanks.
export function LeagueSummary({
  promise,
  stats,
  seasons,
}: {
  promise: Promise<Result<AllTimeStandingsData>>;
  stats: StatItem[];
  seasons: string[];
}) {
  const result = use(promise);
  if (!result.ok) {
    return <ErrorAlert message={result.error} className="my-6" />;
  }
  const { standings, matchups, migrationMapping } = result.data;
  const champions = computeChampions(standings, seasons);
  return (
    <>
      <StatsWithTotalGames
        stats={stats}
        totalGames={computeTotalGames(matchups, seasons)}
        champions={champions}
        totalMembers={computeTotalMembers(matchups, migrationMapping)}
      />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Champions
      </p>
      <ChampionsGrid champions={champions} />
      <AllTimeStandingsTable
        standings={standings}
        matchups={matchups}
        migrationMapping={migrationMapping}
      />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Final Standings Position by Season
      </p>
      <StandingsChart
        standings={standings}
        migrationMapping={migrationMapping}
      />
    </>
  );
}
