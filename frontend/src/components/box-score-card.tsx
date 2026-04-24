import type { PlayerStat } from '@/features/matchups/api-calls';
import { TeamAvatar } from '@/components/team-avatar';

export type { PlayerStat };

export interface BoxScoreSide {
  teamLogo: string | null | undefined;
  teamName: string;
  ownerUsername: string;
  color: string;
  score: number;
  starters: PlayerStat[];
  bench: PlayerStat[];
  isWinner: boolean;
}

const FANTASY_POSITION_ORDER: Record<string, number> = {
  QB: 0,
  RB: 1,
  WR: 2,
  TE: 3,
  FLEX: 4,
  'D/ST': 5,
  K: 6,
};

export function BoxScoreCard({
  left,
  right,
  subtitle,
  platform,
  season,
  onClose,
}: {
  left: BoxScoreSide;
  right: BoxScoreSide;
  subtitle: string;
  platform: 'ESPN' | 'SLEEPER';
  season: string;
  onClose?: () => void;
}) {
  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-3.5 border-b border-border/50 bg-muted">
        <div className="flex items-center gap-2">
          <TeamAvatar
            teamLogo={left.teamLogo ?? null}
            teamName={left.teamName}
            ownerUsername={left.ownerUsername}
            color={left.color}
            size="lg"
          />
          <div>
            <div className="text-[14px] font-medium text-foreground">{left.ownerUsername}</div>
            <div className="text-[11px] text-muted-foreground">{left.teamName}</div>
          </div>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-3">
            <span
              className={`text-[28px] font-medium tabular-nums ${left.isWinner ? 'text-foreground' : 'text-muted-foreground'}`}
            >
              {left.score.toFixed(2)}
            </span>
            <span className="text-[18px] text-muted-foreground">–</span>
            <span
              className={`text-[28px] font-medium tabular-nums ${right.isWinner ? 'text-foreground' : 'text-muted-foreground'}`}
            >
              {right.score.toFixed(2)}
            </span>
          </div>
          {onClose ? (
            <div className="flex items-center justify-center gap-2 mt-0.5">
              <div className="text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground">
                {subtitle}
              </div>
              <button
                className="text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                onClick={onClose}
              >
                ✕
              </button>
            </div>
          ) : (
            <div className="text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground mt-0.5">
              {subtitle}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-row-reverse">
          <TeamAvatar
            teamLogo={right.teamLogo ?? null}
            teamName={right.teamName}
            ownerUsername={right.ownerUsername}
            color={right.color}
            size="lg"
          />
          <div className="text-right">
            <div className="text-[14px] font-medium text-foreground">{right.ownerUsername}</div>
            <div className="text-[11px] text-muted-foreground">{right.teamName}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-border/50">
        {([left, right] as BoxScoreSide[]).map((side, ti) => (
          <div key={ti}>
            <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-border/50">
              <TeamAvatar
                teamLogo={side.teamLogo ?? null}
                teamName={side.teamName}
                ownerUsername={side.ownerUsername}
                color={side.color}
              />
              <div>
                <div className="text-[13px] font-medium text-foreground">{side.ownerUsername}</div>
                <div className="text-[11px] text-muted-foreground">{side.teamName}</div>
              </div>
              {side.isWinner && (
                <span
                  className="ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full"
                  style={{ background: '#EAF3DE', color: '#27500A' }}
                >
                  Winner
                </span>
              )}
            </div>
            <table className="w-full text-[12px]" style={{ tableLayout: 'fixed' }}>
              <thead>
                <tr>
                  <th
                    className="text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted"
                    style={{ width: '52px' }}
                  >
                    Pos
                  </th>
                  <th className="text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                    Player
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted"
                    style={{ width: '64px' }}
                  >
                    Pts
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...side.starters]
                  .sort(
                    (a, b) =>
                      (FANTASY_POSITION_ORDER[a.fantasy_position ?? ''] ?? 99) -
                      (FANTASY_POSITION_ORDER[b.fantasy_position ?? ''] ?? 99),
                  )
                  .map((p) => (
                    <tr key={p.player_id} className="border-b border-border/50 last:border-0">
                      <td className="px-3.5 py-2.5 text-[11px] font-medium text-muted-foreground">
                        {p.fantasy_position ?? p.position}
                      </td>
                      <td className="px-3.5 py-2.5 text-[12px] text-foreground truncate">
                        {p.full_name}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-[12px] tabular-nums text-foreground">
                        {Number(p.points_scored).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                <tr className="bg-muted">
                  <td colSpan={2} className="px-3.5 py-2.5 text-[12px] font-medium text-muted-foreground">
                    Total
                  </td>
                  <td className="px-3.5 py-2.5 text-right font-medium text-foreground tabular-nums">
                    {side.score.toFixed(2)}
                  </td>
                </tr>
                {side.bench.length === 0 && platform === 'ESPN' && Number(season) < 2018 && (
                  <tr>
                    <td colSpan={3} className="px-3.5 py-2.5 text-[11px] text-muted-foreground italic">
                      Bench data unavailable for ESPN seasons prior to 2018.
                    </td>
                  </tr>
                )}
                {side.bench.length > 0 && (
                  <>
                    <tr className="bg-muted">
                      <td
                        colSpan={3}
                        className="px-3.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground"
                      >
                        Bench
                      </td>
                    </tr>
                    {side.bench.map((p) => (
                      <tr key={p.player_id} className="border-b border-border/50 last:border-0">
                        <td className="px-3.5 py-2.5 text-[11px] font-medium text-muted-foreground">
                          {p.position}
                        </td>
                        <td className="px-3.5 py-2.5 text-[12px] text-muted-foreground truncate">
                          {p.full_name}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-[12px] tabular-nums text-muted-foreground">
                          {Number(p.points_scored).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </>
                )}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
