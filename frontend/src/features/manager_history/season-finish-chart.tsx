import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from '@/components/ui/chart';
import { ordinal } from '@/features/manager_history/format';
import { type ManagerData } from '@/features/manager_history/types';

export function SeasonFinishChart({ m }: { m: ManagerData }) {
  const finishValues = m.seasons
    .filter((s) => s.finish !== null)
    .map((s) => s.finish!);
  const maxFinish = finishValues.length > 0 ? Math.max(...finishValues) : 12;
  const rankChartData = m.seasons.map((s) => ({
    year: s.year,
    finish: s.finish,
  }));
  const rankChartConfig: ChartConfig = {
    finish: { label: 'Finish', color: m.color },
  };

  return (
    <>
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Season finish
      </p>
      <div className="bg-card border border-border/50 rounded-lg p-5 mb-6">
        {finishValues.length > 0 ? (
          <ChartContainer
            config={rankChartConfig}
            className="h-48 w-full aspect-auto"
          >
            <LineChart
              data={rankChartData}
              margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
            >
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="year"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
              />
              <YAxis
                reversed
                allowDecimals={false}
                domain={[1, maxFinish]}
                tickFormatter={(v: number) => ordinal(v)}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <ChartTooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const finish = payload[0]?.value;
                  return (
                    <div className="grid min-w-32 items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
                      <p className="font-medium">{String(label)} Season</p>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 shrink-0 rounded-xs"
                          style={{ backgroundColor: m.color }}
                        />
                        <span className="text-muted-foreground">Finish</span>
                        <span className="font-medium text-foreground tabular-nums ml-auto">
                          {finish != null ? ordinal(Number(finish)) : '—'}
                        </span>
                      </div>
                    </div>
                  );
                }}
              />
              <Line
                type="monotone"
                dataKey="finish"
                stroke={`var(--color-finish)`}
                strokeWidth={2}
                dot={{ r: 4, fill: `var(--color-finish)`, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
            </LineChart>
          </ChartContainer>
        ) : (
          <p className="text-[13px] text-muted-foreground text-center py-4">
            No finish data available.
          </p>
        )}
      </div>
    </>
  );
}
