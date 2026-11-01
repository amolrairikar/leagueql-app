import { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import { buildChartData } from '@/features/home_page/chart-data';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';

export function StandingsChart({
  standings,
  migrationMapping,
}: {
  standings: ManagerStandingsItem[];
  migrationMapping: Map<string, string>;
}) {
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);

  const { owners, colorMap, chartData, chartConfig, maxRank } = useMemo(
    () => buildChartData(standings, migrationMapping),
    [standings, migrationMapping],
  );

  if (standings.length === 0) {
    return (
      <div className="bg-card border border-border/50 rounded-lg p-5">
        <p className="text-[13px] text-muted-foreground text-center py-8">
          No standings data available.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5">
      <div className="h-56 w-full">
        <ChartContainer
          config={chartConfig}
          className="h-full w-full aspect-auto"
        >
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="season"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              reversed
              domain={[0.5, maxRank + 0.5]}
              tickLine={false}
              axisLine={false}
              width={28}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => v.toFixed(0)}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => label}
                  indicator="line"
                />
              }
            />
            {owners.map((owner) => {
              const isSelected =
                selectedOwnerId === null || selectedOwnerId === owner.ownerId;
              const opacity =
                selectedOwnerId === null ? 1 : isSelected ? 1 : 0.2;
              return (
                <Line
                  key={owner.ownerId}
                  dataKey={owner.ownerId}
                  stroke={colorMap.get(owner.ownerId)}
                  strokeWidth={2}
                  strokeOpacity={opacity}
                  dot={false}
                  activeDot={{ r: 4 }}
                  type="linear"
                  connectNulls={false}
                />
              );
            })}
          </LineChart>
        </ChartContainer>
      </div>
      <div className="flex flex-wrap gap-4 mt-3">
        {owners.map((owner) => {
          const isSelected =
            selectedOwnerId === null || selectedOwnerId === owner.ownerId;
          const opacity = selectedOwnerId === null ? 1 : isSelected ? 1 : 0.4;
          return (
            <div
              key={owner.ownerId}
              className="flex items-center gap-2 cursor-pointer"
              onClick={() =>
                setSelectedOwnerId(
                  selectedOwnerId === owner.ownerId ? null : owner.ownerId,
                )
              }
              style={{ opacity }}
            >
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: colorMap.get(owner.ownerId) }}
              />
              <span className="text-[11px] text-foreground">
                {owner.username}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
