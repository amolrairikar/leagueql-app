import { useState } from 'react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import type { PowerRankingsData } from './compute-power-rankings';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { avatarColor } from '@/lib/color-constants';

/**
 * Multi-line power-rankings bump chart (FE-033). Each manager is one line of
 * their weekly league rank (1 = best, drawn at the top via a reversed y-axis),
 * derived from the blended power score, so the lines visibly cross over as teams
 * rise and fall. Mirrors the wins progression chart on the standings page: a
 * recharts `LineChart` in a `ChartContainer`, an interactive legend that isolates
 * a single line, and per-manager colors from `avatarColor`. The lines/legend
 * arrive already sorted by latest rank, so the legend doubles as the current
 * standings.
 */
export function PowerRankingsChart({ data }: { data: PowerRankingsData }) {
  const { weeks, teams } = data;
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);

  // Wide format: one row per week, each manager's rank under their team id. The
  // chart is a bump chart of weekly rank (1 = best), so lines visibly cross over.
  const chartData = weeks.map((week) => {
    const point: Record<string, number> = { week };
    for (const team of teams) {
      const pt = team.points.find((p) => p.week === week);
      if (pt) point[team.teamId] = pt.rank;
    }
    return point;
  });

  // Integer rank ticks (1 … N), drawn top-to-bottom via a reversed y-axis.
  const rankTicks = Array.from({ length: teams.length }, (_, i) => i + 1);

  const colorMap = new Map(
    teams.map((team, i) => [team.teamId, avatarColor(i)]),
  );

  const chartConfig: ChartConfig = Object.fromEntries(
    teams.map((team, i) => [
      team.teamId,
      { label: team.ownerUsername, color: avatarColor(i) },
    ]),
  );

  return (
    <>
      <ChartContainer config={chartConfig} className="h-80 w-full aspect-auto">
        <LineChart
          data={chartData}
          margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
        >
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="week"
            tickFormatter={(v: number) => `Wk ${v}`}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
          />
          <YAxis
            reversed
            // Half-unit padding so the rank 1 and rank N ticks aren't clipped
            // against the top/bottom edges of the plot.
            domain={[0.5, teams.length + 0.5]}
            ticks={rankTicks}
            allowDecimals={false}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(_val, payload) =>
                  `Week ${(payload?.[0]?.payload as { week?: string } | undefined)?.week ?? ''}`
                }
                indicator="line"
              />
            }
          />
          {teams.map((team) => {
            const isSelected =
              selectedTeamId === null || selectedTeamId === team.teamId;
            return (
              <Line
                key={team.teamId}
                type="linear"
                dataKey={team.teamId}
                stroke={colorMap.get(team.teamId)}
                strokeWidth={2}
                strokeOpacity={
                  selectedTeamId === null ? 1 : isSelected ? 1 : 0.2
                }
                dot={false}
                activeDot={{ r: 4 }}
                connectNulls
              />
            );
          })}
        </LineChart>
      </ChartContainer>
      <div className="flex flex-wrap gap-4 mt-3">
        {teams.map((team) => {
          const isSelected =
            selectedTeamId === null || selectedTeamId === team.teamId;
          return (
            <div
              key={team.teamId}
              className="flex items-center gap-2 cursor-pointer"
              onClick={() =>
                setSelectedTeamId(
                  selectedTeamId === team.teamId ? null : team.teamId,
                )
              }
              style={{ opacity: isSelected ? 1 : 0.4 }}
            >
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: colorMap.get(team.teamId) }}
              />
              <span className="text-[11px] text-foreground">
                {team.ownerUsername}
              </span>
            </div>
          );
        })}
      </div>
    </>
  );
}
