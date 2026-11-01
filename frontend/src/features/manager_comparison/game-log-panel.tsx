import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import {
  type GameLog,
  type Manager,
} from '@/features/manager_comparison/types';
import { type Platform } from '@/lib/cookie-handler';
import { pct } from '@/lib/utils';

export function MgrAvatar({ color, init }: { color: string; init: string }) {
  return (
    <div
      className="w-14 h-14 rounded-full flex items-center justify-center text-[17px] font-medium text-white shrink-0"
      style={{ background: color }}
    >
      {init}
    </div>
  );
}

export function GameLogPanel({
  left,
  right,
  games,
  selectedIdx,
  onGameSelect,
}: {
  left: Manager;
  right: Manager;
  games: GameLog[];
  selectedIdx: number | null;
  onGameSelect: (idx: number | null) => void;
}) {
  return (
    <div className="absolute inset-0 bg-card border border-border/50 rounded-lg overflow-hidden flex flex-col">
      <div className="px-3.5 py-2.5 border-b border-border/50 bg-muted shrink-0">
        <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-muted-foreground">
          Game Log
        </span>
      </div>

      <div className="overflow-y-auto flex-1 min-h-0">
        {games.length === 0 ? (
          <div className="px-3.5 py-6 text-center text-[13px] text-muted-foreground">
            No matchups played yet.
          </div>
        ) : (
          games.map((g, idx) => {
            const lWin = g.lp > g.rp;
            const isSelected = selectedIdx === idx;
            return (
              <div
                key={idx}
                className={`px-3.5 py-2.5 border-b border-border/50 last:border-0 flex flex-col gap-1.5 cursor-pointer transition-colors ${isSelected ? 'bg-muted' : 'hover:bg-muted/50'}`}
                onClick={() => onGameSelect(isSelected ? null : idx)}
              >
                <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  {g.season} — {g.week}
                </span>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-1.5">
                  <div className="flex items-center gap-1.5">
                    <div
                      className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[9px] font-medium text-white shrink-0"
                      style={{ background: left.color }}
                    >
                      {left.init}
                    </div>
                    <div>
                      <div className="text-[11px] font-medium text-foreground">
                        {left.name}
                      </div>
                      <div
                        className="text-[14px] font-medium"
                        style={{ color: lWin ? left.color : undefined }}
                      >
                        {g.lp.toFixed(1)}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] text-muted-foreground text-center">
                    vs
                  </span>
                  <div className="flex items-center gap-1.5 flex-row-reverse">
                    <div
                      className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[9px] font-medium text-white shrink-0"
                      style={{ background: right.color }}
                    >
                      {right.init}
                    </div>
                    <div className="text-right">
                      <div className="text-[11px] font-medium text-foreground">
                        {right.name}
                      </div>
                      <div
                        className="text-[14px] font-medium"
                        style={{ color: !lWin ? right.color : undefined }}
                      >
                        {g.rp.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-0.75">
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full ml-auto"
                      style={{
                        width: `${pct(g.lp, g.rp)}%`,
                        background: lWin ? left.color : 'var(--color-border)',
                      }}
                    />
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct(g.rp, g.lp)}%`,
                        background: !lWin ? right.color : 'var(--color-border)',
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export function ManagerBoxScoreView({
  game,
  left,
  right,
  platform,
  onClose,
}: {
  game: GameLog;
  left: Manager;
  right: Manager;
  platform: Platform;
  onClose: () => void;
}) {
  const m = game.matchupItem;
  const lWins = game.lp > game.rp;
  const leftSide: BoxScoreSide = {
    teamLogo: game.leftIsA ? m.team_a_team_logo : m.team_b_team_logo,
    teamName:
      (game.leftIsA ? m.team_a_team_name : m.team_b_team_name) ||
      `Team ${left.name}`,
    ownerUsername: left.name,
    color: left.color,
    score: game.lp,
    starters: game.leftIsA ? m.team_a_starters : m.team_b_starters,
    bench: game.leftIsA ? m.team_a_bench : m.team_b_bench,
    isWinner: lWins,
  };
  const rightSide: BoxScoreSide = {
    teamLogo: game.leftIsA ? m.team_b_team_logo : m.team_a_team_logo,
    teamName:
      (game.leftIsA ? m.team_b_team_name : m.team_a_team_name) ||
      `Team ${right.name}`,
    ownerUsername: right.name,
    color: right.color,
    score: game.rp,
    starters: game.leftIsA ? m.team_b_starters : m.team_a_starters,
    bench: game.leftIsA ? m.team_b_bench : m.team_a_bench,
    isWinner: !lWins,
  };
  return (
    <div className="mt-4">
      <BoxScoreCard
        left={leftSide}
        right={rightSide}
        platform={platform}
        season={game.season}
        onClose={onClose}
      />
    </div>
  );
}
