import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';

const managers = [
  { name: 'John', color: '#4338ca' },
  { name: 'Mike', color: '#993c1d' },
  { name: 'Sarah', color: '#0f6e56' },
  { name: 'Alex', color: '#BA7517' },
  { name: 'Chris', color: '#185FA5' },
];

const managerRankings = [
  { season: '2017', John: 3, Mike: 5, Sarah: 7, Alex: 2, Chris: 4 },
  { season: '2018', John: 4, Mike: 1, Sarah: 6, Alex: 3, Chris: 5 },
  { season: '2019', John: 1, Mike: 6, Sarah: 8, Alex: 2, Chris: 4 },
  { season: '2020', John: 5, Mike: 4, Sarah: 1, Alex: 3, Chris: 6 },
  { season: '2021', John: 6, Mike: 5, Sarah: 4, Alex: 1, Chris: 2 },
  { season: '2022', John: 4, Mike: 2, Sarah: 5, Alex: 6, Chris: 3 },
  { season: '2023', John: 5, Mike: 4, Sarah: 3, Alex: 2, Chris: 1 },
  { season: '2024', John: 2, Mike: 3, Sarah: 5, Alex: 1, Chris: 4 },
];

const chartConfig: ChartConfig = {
  John: { label: 'John', color: '#4338ca' },
  Mike: { label: 'Mike', color: '#993c1d' },
  Sarah: { label: 'Sarah', color: '#0f6e56' },
  Alex: { label: 'Alex', color: '#BA7517' },
  Chris: { label: 'Chris', color: '#185FA5' },
};

const champions = [
  { season: '2017', name: 'Mahomes Magic', owner: 'John', record: '10-3', pfGame: '108.6' },
  { season: '2018', name: 'Gronk Nation', owner: 'Mike', record: '11-2', pfGame: '106.8' },
  { season: '2019', name: 'Mahomes Magic', owner: 'John', record: '12-1', pfGame: '115.5' },
  { season: '2020', name: 'Derrick\'s Army', owner: 'Sarah', record: '10-3', pfGame: '112.8' },
  { season: '2021', name: 'Tyreek n Seek', owner: 'Alex', record: '12-1', pfGame: '122.9' },
  { season: '2022', name: 'Gronk Nation', owner: 'Mike', record: '11-2', pfGame: '113.7' },
  { season: '2023', name: 'CMC FC', owner: 'Chris', record: '11-2', pfGame: '117.1' },
  { season: '2024', name: 'TBD', owner: '—', record: '—', pfGame: '—', highlight: true },
];

const stats = [
  { label: 'Seasons played', value: '8', sub: '2017 – 2024' },
  { label: 'Total games', value: '1,120', sub: 'reg + playoffs' },
  { label: 'Avg pts / game', value: '112.4', sub: 'all-time mean' },
  { label: 'Record score', value: '198.7', sub: 'Week 11, 2021' },
  { label: 'Unique champions', value: '6', sub: 'of 10 managers' },
];

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-4xl mx-auto w-full">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground">League Name</h1>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 mb-6">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-card border border-border/50 rounded-md p-3.5 text-center"
            >
              <div className="text-[11px] font-medium tracking-[0.06em] text-muted-foreground mb-1.5">
                {stat.label}
              </div>
              <div className="text-2xl font-bold text-foreground leading-none">
                {stat.value}
              </div>
              <div className="text-[12px] text-muted-foreground mt-1">
                {stat.sub}
              </div>
            </div>
          ))}
        </div>

        {/* Champions */}
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Champions by season
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-7">
          {champions.map((champ) => (
            <div
              key={champ.season}
              className={`bg-card border border-border/50 rounded-md p-2.5 flex flex-col gap-0.5 ${
                champ.highlight
                  ? 'border-primary bg-primary/5'
                  : ''
              }`}
            >
              <div className="text-[10px] tracking-[0.06em] text-muted-foreground">
                {champ.season}
              </div>
              <div className="text-[13px] font-bold text-foreground leading-tight">
                {champ.name}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {champ.owner}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {champ.record} · {champ.pfGame} PF/G
              </div>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="bg-card border border-border/50 rounded-lg p-5">
          <div className="mb-4">
            <div className="text-[14px] font-bold text-foreground">
              Manager finishing ranks by season
            </div>
          </div>
          <div className="h-56 w-full">
            <ChartContainer config={chartConfig} className="h-full w-full aspect-auto">
              <LineChart data={managerRankings} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
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
                  domain={[0.5, 10.5]}
                  tickLine={false}
                  axisLine={false}
                  width={28}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => v.toFixed(0)}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      labelFormatter={(label) => `${label}`}
                      indicator="line"
                    />
                  }
                />
                <ChartLegend content={<ChartLegendContent className="flex-wrap" />} />
                {managers.map((manager) => (
                  <Line
                    key={manager.name}
                    dataKey={manager.name}
                    stroke={manager.color}
                    strokeWidth={2}
                    dot={{ fill: manager.color, r: 4 }}
                    activeDot={{ r: 6 }}
                    type="monotone"
                  />
                ))}
              </LineChart>
            </ChartContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
