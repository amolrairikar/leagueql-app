import {
  CartesianGrid,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

import {
  comparePositions,
  type DraftScatterPoint,
  positionLabel,
} from './compute-draft-scatter';

import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from '@/components/ui/chart';
import { positionColorMeta } from '@/lib/color-constants';

/**
 * Tooltip for a hovered dot (frontend/draft-value-scatter): the player, the manager who drafted them,
 * the points scored, and the draft position. Exported so it can be unit-tested
 * without driving a recharts hover (unreliable in jsdom).
 */
export function DraftScatterTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: DraftScatterPoint }[];
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-popover-foreground shadow-md">
      <p className="text-[13px] font-medium">{point.player}</p>
      <p className="text-[11px] text-muted-foreground">
        Drafted by {point.manager}
      </p>
      <div className="mt-1 grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 text-[11px]">
        <span className="text-muted-foreground">Points</span>
        <span className="text-right font-medium tabular-nums text-foreground">
          {point.points.toFixed(1)}
        </span>
        <span className="text-muted-foreground">Draft position</span>
        <span className="text-right font-medium tabular-nums text-foreground">
          #{point.pick}
        </span>
      </div>
    </div>
  );
}

/**
 * Scatterplot of draft value (frontend/draft-value-scatter): draft position (x) vs. season points (y),
 * one dot per scored pick, grouped into a series per position so each is colored
 * from the shared position palette ({@link positionColorMeta}) and appears in the
 * legend. `points` is already filtered to the selected position by the caller; the
 * rendered series and legend derive from whatever positions remain.
 */
export function DraftScatterChart({ points }: { points: DraftScatterPoint[] }) {
  // Positions present in the (filtered) points, ordered QB → RB → WR → TE → D/ST
  // → K so the series and legend read in the canonical fantasy order.
  const byPosition = new Map<string, DraftScatterPoint[]>();
  for (const p of points) {
    const bucket = byPosition.get(p.position);
    if (bucket) bucket.push(p);
    else byPosition.set(p.position, [p]);
  }
  const positions = [...byPosition.keys()].sort(comparePositions);

  const chartConfig: ChartConfig = Object.fromEntries(
    positions.map((pos) => [
      pos,
      { label: positionLabel(pos), color: positionColorMeta(pos).color },
    ]),
  );

  return (
    <>
      <ChartContainer config={chartConfig} className="w-full aspect-auto h-80">
        <ScatterChart margin={{ top: 8, right: 12, left: 8, bottom: 20 }}>
          <CartesianGrid />
          <XAxis
            type="number"
            dataKey="pick"
            name="Draft position"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            label={{
              value: 'Draft position',
              position: 'insideBottom',
              offset: -12,
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="points"
            name="Points"
            tickLine={false}
            axisLine={false}
            tickMargin={4}
            width={68}
            label={{
              value: 'Points',
              angle: -90,
              position: 'insideLeft',
              offset: 0,
              fontSize: 11,
            }}
          />
          <ZAxis range={[45, 45]} />
          <ChartTooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={<DraftScatterTooltip />}
          />
          {positions.map((pos) => (
            <Scatter
              key={pos}
              name={positionLabel(pos)}
              data={byPosition.get(pos)}
              fill={positionColorMeta(pos).color}
              fillOpacity={0.75}
            />
          ))}
        </ScatterChart>
      </ChartContainer>
      <div className="flex flex-wrap gap-4 mt-3">
        {positions.map((pos) => (
          <div key={pos} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: positionColorMeta(pos).color }}
            />
            <span className="text-[11px] text-foreground">
              {positionLabel(pos)}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
