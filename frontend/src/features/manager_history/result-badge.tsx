import { POSITION_COLORS, UI_COLORS } from '@/lib/color-constants';

export function resultBadge(result: string) {
  if (result === 'champion')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{
          background: UI_COLORS.champion.bg,
          color: UI_COLORS.champion.text,
        }}
      >
        Champion
      </span>
    );
  if (result === 'runner')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{
          background: POSITION_COLORS.TE.bg,
          color: POSITION_COLORS.TE.tc,
        }}
      >
        Runner-up
      </span>
    );
  if (result === 'playoff')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{
          background: POSITION_COLORS.RB.bg,
          color: POSITION_COLORS.RB.tc,
        }}
      >
        Playoffs
      </span>
    );
  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
      style={{ background: POSITION_COLORS.K.bg, color: POSITION_COLORS.K.tc }}
    >
      <span className="whitespace-nowrap">Missed Playoffs</span>
    </span>
  );
}
