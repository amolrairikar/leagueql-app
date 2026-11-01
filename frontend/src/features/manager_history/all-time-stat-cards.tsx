import { type ManagerData } from '@/features/manager_history/types';

export function AllTimeStatCards({ m }: { m: ManagerData }) {
  const at = m.allTime;
  const winPct =
    at.wins + at.losses > 0
      ? (at.wins / (at.wins + at.losses)).toFixed(3)
      : '0.000';

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mb-6">
      <div className="bg-card border border-border/50 rounded-lg p-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
          All-time record
        </div>
        <div className="text-[22px] font-medium text-foreground">
          {at.wins}-{at.losses}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          {winPct} win percentage
        </div>
      </div>
      <div className="bg-card border border-border/50 rounded-lg p-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
          Championships
        </div>
        <div className="text-[22px] font-medium text-foreground">
          {at.championships}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          of {m.seasons.length} seasons
        </div>
      </div>
      <div className="bg-card border border-border/50 rounded-lg p-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
          Playoff apps
        </div>
        <div className="text-[22px] font-medium text-foreground">
          {at.playoffs}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          of {m.seasons.length} seasons
        </div>
      </div>
      <div className="bg-card border border-border/50 rounded-lg p-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
          Avg pts / wk
        </div>
        <div className="text-[22px] font-medium text-foreground">
          {at.avgPts.toFixed(1)}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">all-time</div>
      </div>
      <div className="bg-card border border-border/50 rounded-lg p-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
          High score
        </div>
        <div className="text-[22px] font-medium text-foreground">
          {at.highScore.toFixed(2)}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          single week
        </div>
      </div>
    </div>
  );
}
