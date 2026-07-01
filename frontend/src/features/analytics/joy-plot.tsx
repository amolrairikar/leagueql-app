import { useEffect, useRef, useState } from 'react';

import type {
  RidgeStats,
  ScoreDistributionData,
} from './compute-score-distribution';

import { TeamAvatar } from '@/components/team-avatar';
import { avatarColor } from '@/lib/color-constants';

const LABEL_W = 150; // px reserved for the manager avatar + name column
const ROW_STEP = 32; // px vertical distance between adjacent ridge baselines
const RIDGE_H = 54; // px height of the tallest (max-density) ridge peak
const TOP_PAD = RIDGE_H; // px headroom so the top ridge isn't clipped
const BOTTOM_PAD = 6; // px below the last baseline
const PAD_X = 14; // px horizontal inset so the curve tails don't clip
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

/** One-line accessible summary of a manager's ridge, mirroring the tooltip. */
function summarize(team: RidgeStats): string {
  return `${team.ownerUsername}: mean ${fmt(team.mean)}, median ${fmt(
    team.median,
  )}, min ${fmt(team.min)}, max ${fmt(team.max)}, std dev ${fmt(team.stdev)}`;
}

/** Interpolate a manager's density at an arbitrary x from the shared grid. */
function densityAt(grid: number[], density: number[], xv: number): number {
  if (xv <= grid[0]) return density[0];
  const last = grid.length - 1;
  if (xv >= grid[last]) return density[last];
  for (let j = 1; j <= last; j++) {
    if (grid[j] >= xv) {
      const t = (xv - grid[j - 1]) / (grid[j] - grid[j - 1]);
      return density[j - 1] + (density[j] - density[j - 1]) * t;
    }
  }
  return 0;
}

/** Cursor-anchored hover state, in container-relative pixels. */
interface Hover {
  team: RidgeStats;
  color: string;
  left: number;
  baseline: number;
}

/**
 * Per-manager ridgeline ("joy") chart of weekly scores (FE-033). Custom SVG
 * because recharts has no native ridgeline. Every manager's Gaussian-KDE curve
 * shares one x-scale and one vertical density scale, so a steadier manager draws
 * a taller/narrower ridge and a volatile one a lower/flatter ridge — directly
 * comparable. Ridges overlap and are painted top→bottom so each front (lower)
 * ridge occludes the tail of the one behind it. Hovering or focusing a ridge
 * surfaces a tooltip with that manager's numbers (see "Hover detail" in the doc).
 */
export function JoyPlot({ data }: { data: ScoreDistributionData }) {
  const { teams, globalMin, globalMax, grid, maxDensity } = data;
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

  const gridLo = grid[0];
  const gridHi = grid[grid.length - 1];
  const x = (v: number) =>
    PAD_X + ((v - gridLo) / (gridHi - gridLo)) * (plotW - 2 * PAD_X);

  const baselineOf = (i: number) => TOP_PAD + i * ROW_STEP;
  const plotH = TOP_PAD + (teams.length - 1) * ROW_STEP + BOTTOM_PAD;

  const showHover =
    (team: RidgeStats, color: string, i: number) =>
    (e: { clientX: number }) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      // Anchor horizontally to the cursor, clamped so the tooltip stays on screen.
      const left = Math.min(
        Math.max(e.clientX - rect.left, TOOLTIP_W / 2 + 4),
        rect.width - TOOLTIP_W / 2 - 4,
      );
      setHover({ team, color, left, baseline: baselineOf(i) });
    };

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative" style={{ height: plotH }}>
        {/* Ridges: painted in order so the last (bottom) ridge is on top. */}
        <svg
          className="absolute overflow-visible"
          style={{ left: LABEL_W, top: 0 }}
          width={plotW}
          height={plotH}
          role="presentation"
        >
          {teams.map((team, i) => (
            <Ridge
              key={team.teamId}
              team={team}
              color={avatarColor(i)}
              baseline={baselineOf(i)}
              x={x}
              grid={grid}
              maxDensity={maxDensity}
              active={hover?.team.teamId === team.teamId}
            />
          ))}
        </svg>

        {/* Manager labels, aligned to each ridge baseline. */}
        {teams.map((team, i) => (
          <div
            key={team.teamId}
            className="absolute flex items-center gap-2 -translate-y-1/2 pr-3"
            style={{ left: 0, top: baselineOf(i), width: LABEL_W }}
          >
            <TeamAvatar
              teamLogo={team.teamLogo}
              teamName={team.teamName}
              ownerUsername={team.ownerUsername}
              color={avatarColor(i)}
            />
            <span className="text-[12px] font-medium text-foreground truncate">
              {team.ownerUsername}
            </span>
          </div>
        ))}

        {/* Transparent hit areas (on top) carry hover + keyboard focus + a11y. */}
        {teams.map((team, i) => (
          <div
            key={team.teamId}
            className="absolute -translate-y-1/2 rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            style={{ left: 0, right: 0, top: baselineOf(i), height: ROW_STEP }}
            tabIndex={0}
            role="img"
            aria-label={summarize(team)}
            onMouseMove={showHover(team, avatarColor(i), i)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => showHover(team, avatarColor(i), i)({ clientX: 0 })}
            onBlur={() => setHover(null)}
          />
        ))}
      </div>

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

function Ridge({
  team,
  color,
  baseline,
  x,
  grid,
  maxDensity,
  active,
}: {
  team: RidgeStats;
  color: string;
  baseline: number;
  x: (v: number) => number;
  grid: number[];
  maxDensity: number;
  active: boolean;
}) {
  const y = (density: number) => baseline - (density / maxDensity) * RIDGE_H;

  // Area path: baseline at the left edge, up over the curve, back down to the
  // baseline at the right edge, then closed.
  const top = grid
    .map((gx, j) => `${x(gx).toFixed(2)},${y(team.density[j]).toFixed(2)}`)
    .join(' L ');
  const path = `M ${x(grid[0]).toFixed(2)},${baseline} L ${top} L ${x(
    grid[grid.length - 1],
  ).toFixed(2)},${baseline} Z`;

  const medianTop = y(densityAt(grid, team.density, team.median));

  return (
    <g>
      {/* Opaque backdrop so this ridge occludes the ones behind (above) it. */}
      <path d={path} className="fill-card" />
      <path
        d={path}
        fill={color}
        fillOpacity={active ? 0.35 : 0.22}
        stroke={color}
        strokeWidth={active ? 2 : 1.5}
        strokeLinejoin="round"
      />
      {/* Thin median marker */}
      <line
        x1={x(team.median)}
        x2={x(team.median)}
        y1={baseline}
        y2={medianTop}
        stroke={color}
        strokeWidth={active ? 1.5 : 1}
        strokeOpacity={0.7}
      />
    </g>
  );
}

/**
 * Floating numeric summary anchored to the hovered/focused ridge. Rendered above
 * the ridge by default, but flipped below when the ridge is near the top of the
 * chart so it never floats up into the clipped/scrolled-off area.
 */
function Tooltip({ hover }: { hover: Hover }) {
  const { team, color, left, baseline } = hover;
  const above = baseline - RIDGE_H - 6;
  const below = above < TOOLTIP_H;
  return (
    <div
      role="presentation"
      className={`pointer-events-none absolute z-20 -translate-x-1/2 rounded-md border border-border bg-popover px-3 py-2 text-popover-foreground shadow-md ${
        below ? '' : '-translate-y-full'
      }`}
      style={{
        left,
        top: below ? baseline + 8 : above,
        width: TOOLTIP_W,
      }}
    >
      <div className="mb-1.5 flex items-center gap-1.5">
        <span
          className="inline-block size-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="truncate text-[12px] font-semibold">
          {team.ownerUsername}
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] tabular-nums">
        <Stat label="Mean" value={fmt(team.mean)} />
        <Stat label="Median" value={fmt(team.median)} />
        <Stat label="Min" value={fmt(team.min)} />
        <Stat label="Max" value={fmt(team.max)} />
        <Stat label="Std dev" value={fmt(team.stdev)} />
      </dl>
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
