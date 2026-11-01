import { Fragment, useEffect, useRef, useState } from 'react';

import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import {
  type BoxScoreSideData,
  type ScheduleGame,
  type SeasonEntry,
} from '@/features/manager_history/types';
import { UI_COLORS } from '@/lib/color-constants';
import { type Platform } from '@/lib/cookie-handler';

export function SeasonSchedulePanel({
  season,
  platform,
}: {
  season: SeasonEntry;
  platform: Platform;
}) {
  const [selectedGame, setSelectedGame] = useState<ScheduleGame | null>(null);
  const boxScoreRef = useRef<HTMLDivElement>(null);

  // Scroll the box score into view when a game is selected (matters on mobile,
  // where the box score stacks below the schedule)
  useEffect(() => {
    if (selectedGame) {
      boxScoreRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [selectedGame]);

  const resultColor = (r: 'W' | 'L' | 'T') =>
    r === 'W' ? UI_COLORS.positive : r === 'L' ? UI_COLORS.negative : undefined;

  const toSide = (s: BoxScoreSideData): BoxScoreSide => ({
    teamLogo: s.teamLogo,
    teamName: s.teamName,
    ownerUsername: s.ownerUsername,
    color: s.color,
    score: s.score,
    starters: s.starters,
    bench: s.bench,
    isWinner: s.isWinner,
  });

  return (
    <div className="flex flex-col md:flex-row gap-6">
      <div className={selectedGame ? 'md:w-80 md:shrink-0' : 'w-full'}>
        <table className="w-full text-[13px] border-separate border-spacing-0">
          <thead>
            <tr className="text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
              <th className="text-left font-medium py-2 pr-2">Wk</th>
              <th className="text-left font-medium py-2 px-2">Opponent</th>
              <th className="text-center font-medium py-2 px-2">Result</th>
              <th className="text-right font-medium py-2 pl-2">Score</th>
            </tr>
          </thead>
          <tbody>
            {season.schedule.map((g, i) => {
              const isFirstPostseason =
                g.isPostseason && !season.schedule[i - 1]?.isPostseason;
              const isSelected =
                selectedGame?.week === g.week &&
                selectedGame?.opp.ownerId === g.opp.ownerId;
              return (
                <Fragment key={`${g.week}-${g.opp.ownerId}-${g.opp.score}`}>
                  {isFirstPostseason && (
                    <tr>
                      <td
                        colSpan={4}
                        className="pt-3 pb-1.5 text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground"
                      >
                        Postseason
                      </td>
                    </tr>
                  )}
                  <tr
                    onClick={() => setSelectedGame(g)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-accent/60' : 'hover:bg-accent/40'
                    }`}
                  >
                    <td className="py-2 pr-2 text-muted-foreground tabular-nums border-b border-border/40 align-top">
                      {g.week}
                    </td>
                    <td className="py-2 px-2 border-b border-border/40">
                      <div className="font-medium text-foreground">
                        {g.opp.teamName || g.opp.ownerUsername || 'Bye'}
                      </div>
                    </td>
                    <td className="py-2 px-2 text-center border-b border-border/40">
                      <span
                        className="font-medium"
                        style={{ color: resultColor(g.result) }}
                      >
                        {g.result}
                      </span>
                    </td>
                    <td className="py-2 pl-2 text-right tabular-nums font-medium text-foreground border-b border-border/40">
                      {g.own.score.toFixed(1)}–{g.opp.score.toFixed(1)}
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedGame && (
        <div ref={boxScoreRef} className="flex-1 min-w-0 scroll-mt-4">
          <BoxScoreCard
            left={toSide(selectedGame.own)}
            right={toSide(selectedGame.opp)}
            platform={platform}
            season={season.year}
            onClose={() => setSelectedGame(null)}
          />
        </div>
      )}
    </div>
  );
}

// ── Season card ───────────────────────────────────────────────────────────────
