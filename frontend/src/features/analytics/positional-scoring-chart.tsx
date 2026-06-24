import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';

import {
  OTHER_POSITION,
  type PositionalScoringData,
} from './compute-positional-scoring';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { positionColorMeta } from '@/lib/color-constants';

/** Distinct accent for the catch-all 'Other' bucket (positionColorMeta maps it to K). */
const OTHER_COLOR = '#ca8a04';

/**
 * Color for a stacking segment from the shared position palette
 * ({@link positionColorMeta}), so a position reads as its usual color across the
 * app; the accents are tuned for contrast so adjacent segments stay distinct.
 */
function positionColor(position: string): string {
  return position === OTHER_POSITION
    ? OTHER_COLOR
    : positionColorMeta(position).color;
}

/** Position abbreviation shown in the tooltip and legend (DEF renders as D/ST). */
function positionLabel(position: string): string {
  if (position === OTHER_POSITION) return 'Other';
  return position === 'DEF' ? 'D/ST' : position;
}

/**
 * Stacked horizontal bar chart of each manager's total season starter points,
 * split by real position (FE-036). One bar per manager (rows so long names stay
 * legible), segments stacked QB→K→Other and colored from the shared position
 * palette ({@link positionColorMeta}), whose accents are tuned for contrast so
 * adjacent segments stay distinct. A pure render of the
 * `computePositionalScoring` transform. The legend
 * below is real DOM (not dependent on chart measurement), mirroring the
 * power-rankings chart.
 */
export function PositionalScoringChart({
  data,
}: {
  data: PositionalScoringData;
}) {
  const { positions, teams } = data;

  // Wide format: one row per manager, each position's summed points under its key.
  const chartData = teams.map((team) => {
    const row: Record<string, string | number> = { owner: team.ownerUsername };
    for (const pos of positions) row[pos] = team.byPosition[pos] ?? 0;
    return row;
  });

  const chartConfig: ChartConfig = Object.fromEntries(
    positions.map((pos) => [
      pos,
      { label: positionLabel(pos), color: positionColor(pos) },
    ]),
  );

  // Give each bar a little vertical room so a full league isn't cramped.
  const height = Math.max(320, teams.length * 44);

  // Widen the category axis to fit the longest owner name so it isn't clipped.
  const longestName = teams.reduce(
    (max, t) => Math.max(max, t.ownerUsername.length),
    0,
  );
  const yAxisWidth = Math.min(240, Math.max(88, longestName * 8 + 12));

  return (
    <>
      <ChartContainer
        config={chartConfig}
        className="w-full aspect-auto"
        style={{ height }}
      >
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 4, right: 12, left: 0, bottom: 4 }}
        >
          <CartesianGrid horizontal={false} />
          <XAxis
            type="number"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
          />
          <YAxis
            type="category"
            dataKey="owner"
            tickLine={false}
            axisLine={false}
            interval={0}
            width={yAxisWidth}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value, name, item) => (
                  <div className="flex w-full items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-xs"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-muted-foreground">
                      {positionLabel(String(name))}
                    </span>
                    <span className="ml-auto pl-3 font-medium text-foreground tabular-nums">
                      {Number(value).toFixed(1)}
                    </span>
                  </div>
                )}
              />
            }
          />
          {positions.map((pos) => (
            <Bar
              key={pos}
              dataKey={pos}
              stackId="a"
              fill={positionColor(pos)}
              radius={0}
            />
          ))}
        </BarChart>
      </ChartContainer>
      <div className="flex flex-wrap gap-4 mt-3">
        {positions.map((pos) => (
          <div key={pos} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: positionColor(pos) }}
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
