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
const TOOLTIP_W = 220; // px width used to clamp the floating tooltip on screen
const TOOLTIP_H = 150; // px approx tooltip height, used to decide above/below flip

function fmt(n: number): string {
  return n.toFixed(1);
}

/** Five evenly-spaced axis tick values spanning [lo, hi]. */
function axisTicks(lo: number, hi: number): number[] {
  if (hi <= lo) return [lo];
  return Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
}

/** One-line accessible/native summary of a manager's box. */
function summarize(team: BoxStats): string {
  return `${team.ownerUsername}: min ${fmt(team.min)}, Q1 ${fmt(
    team.q1,
  )}, median ${fmt(team.median)}, Q3 ${fmt(team.q3)}, max ${fmt(team.max)}`;
}

/** Cursor-anchored hover state, in container-relative pixels. */
interface Hover {
  team: BoxStats;
  color: string;
  left: number;
  top: number;
}

/**
 * Per-manager horizontal box-and-whisker chart (FE-033). Custom SVG because
 * recharts has no native box plot. All rows share one x-scale spanning the
 * season's global min→max so distributions are directly comparable. Hovering or
 * focusing a row surfaces a tooltip with that manager's numbers (see "Hover
 * detail" in the feature doc).
 */
export function BoxPlot({ data }: { data: ScoreDistributionData }) {
  const { teams, globalMin, globalMax } = data;
  const containerRef = useRef<HTMLDivElement>(null);
  const [plotW, setPlotW] = useState(DEFAULT_PLOT_W);
  const [hover, setHover] = useState<Hover | null>(null);

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

  const showHover =
    (team: BoxStats, color: string) => (e: { clientX: number }) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      // Anchor horizontally to the cursor, clamped so the tooltip stays on screen.
      const left = Math.min(
        Math.max(e.clientX - rect.left, TOOLTIP_W / 2 + 4),
        rect.width - TOOLTIP_W / 2 - 4,
      );
      const top = teams.indexOf(team) * ROW_H;
      setHover({ team, color, left, top });
    };

  return (
    <div ref={containerRef} className="relative w-full">
      {teams.map((team, i) => (
        <Row
          key={team.teamId}
          team={team}
          color={avatarColor(i)}
          x={x}
          plotW={plotW}
          active={hover?.team.teamId === team.teamId}
          onHover={showHover(team, avatarColor(i))}
          onLeave={() => setHover(null)}
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

      {hover && <Tooltip hover={hover} />}
    </div>
  );
}

/**
 * Floating numeric summary anchored to the hovered/focused row. Rendered above
 * the row by default, but flipped below when the row is near the top of the
 * chart so it never floats up into the clipped/scrolled-off area.
 */
function Tooltip({ hover }: { hover: Hover }) {
  const { team, color, left, top } = hover;
  const below = top < TOOLTIP_H;
  return (
    <div
      role="presentation"
      className={`pointer-events-none absolute z-20 -translate-x-1/2 rounded-md border border-border bg-popover px-3 py-2 text-popover-foreground shadow-md ${
        below ? '' : '-translate-y-full'
      }`}
      style={{ left, top: below ? top + ROW_H + 6 : top - 6, width: TOOLTIP_W }}
    >
      <div className="mb-1.5 flex items-center gap-1.5">
        <span
          className="inline-block size-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="truncate text-[12px] font-semibold">
          {team.ownerUsername}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground">
          n={team.scores.length}
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] tabular-nums">
        <Stat label="Median" value={fmt(team.median)} />
        <Stat label="IQR" value={fmt(team.iqr)} />
        <Stat label="Q1" value={fmt(team.q1)} />
        <Stat label="Q3" value={fmt(team.q3)} />
        <Stat label="Whisker low" value={fmt(team.whiskerLow)} />
        <Stat label="Whisker high" value={fmt(team.whiskerHigh)} />
        <Stat label="Min" value={fmt(team.min)} />
        <Stat label="Max" value={fmt(team.max)} />
      </dl>
      {team.outliers.length > 0 && (
        <p className="mt-1.5 text-[10px] text-muted-foreground">
          Outliers: {team.outliers.map(fmt).join(', ')}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function Row({
  team,
  color,
  x,
  plotW,
  active,
  onHover,
  onLeave,
}: {
  team: BoxStats;
  color: string;
  x: (v: number) => number;
  plotW: number;
  active: boolean;
  onHover: (e: { clientX: number }) => void;
  onLeave: () => void;
}) {
  const cy = ROW_H / 2;
  const boxTop = cy - BOX_H / 2;
  const summary = summarize(team);

  return (
    <div
      className={`flex items-center rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active ? 'bg-muted' : ''
      }`}
      style={{ height: ROW_H }}
      tabIndex={0}
      role="img"
      aria-label={summary}
      onMouseMove={onHover}
      onMouseLeave={onLeave}
      onFocus={() => onHover({ clientX: 0 })}
      onBlur={onLeave}
    >
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
          fillOpacity={active ? 0.3 : 0.18}
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
