import { useEffect, useRef, useState } from 'react';

import type {
  BoxStats,
  ScoreDistributionData,
} from './compute-score-distribution';

import { TeamAvatar } from '@/components/team-avatar';
import { avatarColor } from '@/lib/color-constants';

const LABEL_W = 150; // px reserved for the manager avatar + name column
const ROW_H = 40; // px height of each manager's row
const BOX_H = 18; // px vertical height of the IQR box
const CAP_H = 10; // px vertical height of the whisker end caps
const PAD_X = 14; // px horizontal inset so caps/outliers don't clip
const AXIS_H = 22; // px height of the bottom axis row
const DEFAULT_PLOT_W = 640; // px fallback width before ResizeObserver measures

function fmt(n: number): string {
  return n.toFixed(1);
}

/** Five evenly-spaced axis tick values spanning [lo, hi]. */
function axisTicks(lo: number, hi: number): number[] {
  if (hi <= lo) return [lo];
  return Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
}

/**
 * Per-manager horizontal box-and-whisker chart (FE-033). Custom SVG because
 * recharts has no native box plot. All rows share one x-scale spanning the
 * season's global min→max so distributions are directly comparable.
 */
export function BoxPlot({ data }: { data: ScoreDistributionData }) {
  const { teams, globalMin, globalMax } = data;
  const containerRef = useRef<HTMLDivElement>(null);
  const [plotW, setPlotW] = useState(DEFAULT_PLOT_W);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setPlotW(Math.max(160, el.clientWidth - LABEL_W));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Pad the domain slightly so the extreme whiskers/outliers aren't on the edge.
  const range = globalMax - globalMin || 1;
  const domainMin = globalMin - range * 0.05;
  const domainMax = globalMax + range * 0.05;
  const x = (v: number) =>
    PAD_X + ((v - domainMin) / (domainMax - domainMin)) * (plotW - 2 * PAD_X);

  return (
    <div ref={containerRef} className="w-full">
      {teams.map((team, i) => (
        <Row
          key={team.teamId}
          team={team}
          color={avatarColor(i)}
          x={x}
          plotW={plotW}
        />
      ))}
      {/* Shared bottom axis */}
      <div className="flex items-center" style={{ height: AXIS_H }}>
        <div style={{ width: LABEL_W }} className="shrink-0" />
        <svg
          width={plotW}
          height={AXIS_H}
          role="presentation"
          className="overflow-visible"
        >
          {axisTicks(globalMin, globalMax).map((t) => (
            <text
              key={t}
              x={x(t)}
              y={14}
              textAnchor="middle"
              className="fill-muted-foreground text-[10px] tabular-nums"
            >
              {Math.round(t)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}

function Row({
  team,
  color,
  x,
  plotW,
}: {
  team: BoxStats;
  color: string;
  x: (v: number) => number;
  plotW: number;
}) {
  const cy = ROW_H / 2;
  const boxTop = cy - BOX_H / 2;
  const summary = `${team.ownerUsername}: min ${fmt(team.min)}, Q1 ${fmt(
    team.q1,
  )}, median ${fmt(team.median)}, Q3 ${fmt(team.q3)}, max ${fmt(team.max)}`;

  return (
    <div className="flex items-center" style={{ height: ROW_H }}>
      <div
        className="flex items-center gap-2 shrink-0 pr-3"
        style={{ width: LABEL_W }}
      >
        <TeamAvatar
          teamLogo={team.teamLogo}
          teamName={team.teamName}
          ownerUsername={team.ownerUsername}
          color={color}
        />
        <span className="text-[12px] font-medium text-foreground truncate">
          {team.ownerUsername}
        </span>
      </div>
      <svg width={plotW} height={ROW_H} className="overflow-visible">
        <title>{summary}</title>
        {/* Whisker line */}
        <line
          x1={x(team.whiskerLow)}
          x2={x(team.whiskerHigh)}
          y1={cy}
          y2={cy}
          stroke={color}
          strokeWidth={1.5}
        />
        {/* Whisker caps */}
        <line
          x1={x(team.whiskerLow)}
          x2={x(team.whiskerLow)}
          y1={cy - CAP_H / 2}
          y2={cy + CAP_H / 2}
          stroke={color}
          strokeWidth={1.5}
        />
        <line
          x1={x(team.whiskerHigh)}
          x2={x(team.whiskerHigh)}
          y1={cy - CAP_H / 2}
          y2={cy + CAP_H / 2}
          stroke={color}
          strokeWidth={1.5}
        />
        {/* IQR box */}
        <rect
          x={x(team.q1)}
          y={boxTop}
          width={Math.max(1, x(team.q3) - x(team.q1))}
          height={BOX_H}
          fill={color}
          fillOpacity={0.18}
          stroke={color}
          strokeWidth={1.5}
          rx={2}
        />
        {/* Median line */}
        <line
          x1={x(team.median)}
          x2={x(team.median)}
          y1={boxTop}
          y2={boxTop + BOX_H}
          stroke={color}
          strokeWidth={2}
        />
        {/* Outliers */}
        {team.outliers.map((o, idx) => (
          <circle
            key={`${o}-${idx}`}
            cx={x(o)}
            cy={cy}
            r={2.5}
            fill="none"
            stroke={color}
            strokeWidth={1.25}
          />
        ))}
      </svg>
    </div>
  );
}
