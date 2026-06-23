/**
 * Lineup-efficiency computation (FE-035) — pure, no I/O.
 *
 * Computes each manager-week's **optimal legal starting lineup** from the
 * combined `starters + bench` pool in a box score and compares it to what they
 * actually started, surfacing lineup-efficiency %, points left on the bench, and
 * a slot-by-slot start/sit report.
 *
 * The key nuance is **slot eligibility**: the optimal lineup must respect the
 * league's roster slots (FLEX/superflex), not just take the top-N scores. There
 * is no stored per-league roster config, so the slot template is derived from the
 * `fantasy_position` labels of the actual starters, and slot→position eligibility
 * is encoded in {@link SLOT_ELIGIBILITY}. Because the eligibility sets are
 * non-laminar (e.g. an "RB/WR" slot's (RB,WR) overlaps a "WR/TE" slot's (WR,TE)
 * without nesting), a greedy "fill the most-restrictive slot first" can be
 * strictly suboptimal — so the optimum is found as an exact max-weight bipartite
 * matching via min-cost max-flow (see {@link optimalLineup}).
 */
import type { PlayerStat } from '@/components/api/types';
import { POS_NORMALIZE } from '@/lib/position-constants';

/** Normalize a position/slot label across platforms (e.g. ESPN `D/ST` → `DEF`). */
function normalize(label: string): string {
  return POS_NORMALIZE[label] ?? label;
}

/**
 * Maps each starting-slot label (normalized) to the set of real positions
 * (normalized) eligible to fill it. Keys mirror the slot vocabulary in
 * `FANTASY_POSITION_ORDER`. A slot not listed here falls back to only its own
 * label (see {@link eligiblePositions}), so an unseen slot can never crash the
 * optimizer — it just matches a player of the same position.
 */
export const SLOT_ELIGIBILITY: Record<string, Set<string>> = {
  QB: new Set(['QB']),
  TQB: new Set(['QB']),
  // Superflex / "offensive player" slot.
  OP: new Set(['QB', 'RB', 'WR', 'TE']),
  RB: new Set(['RB']),
  'RB/WR': new Set(['RB', 'WR']),
  WR: new Set(['WR']),
  'WR/TE': new Set(['WR', 'TE']),
  TE: new Set(['TE']),
  FLEX: new Set(['RB', 'WR', 'TE']),
  DEF: new Set(['DEF']),
  K: new Set(['K']),
  // IDP slots.
  DL: new Set(['DL', 'DE', 'DT', 'EDR']),
  DE: new Set(['DE']),
  DT: new Set(['DT']),
  EDR: new Set(['EDR', 'DE']),
  LB: new Set(['LB']),
  DB: new Set(['DB', 'CB', 'S']),
  CB: new Set(['CB']),
  S: new Set(['S']),
  // Generic IDP flex.
  DP: new Set(['DL', 'DE', 'DT', 'EDR', 'LB', 'DB', 'CB', 'S']),
  P: new Set(['P']),
  HC: new Set(['HC']),
};

/** Eligible (normalized) positions for a slot label, falling back to its own label. */
function eligiblePositions(slot: string): Set<string> {
  const key = normalize(slot);
  return SLOT_ELIGIBILITY[key] ?? new Set([key]);
}

/** Coerce a possibly-stringy points value to a finite number (non-finite → 0). */
function points(p: PlayerStat): number {
  const n = Number(p.points_scored);
  return Number.isFinite(n) ? n : 0;
}

/** The slot a starter occupied: its `fantasy_position`, falling back to position. */
function slotOf(starter: PlayerStat): string {
  return starter.fantasy_position ?? starter.position;
}

/**
 * The league's starting-slot template for a team-week, derived by tallying the
 * `fantasy_position` of each actual starter (one slot instance per starter).
 */
export function deriveRequiredSlots(starters: PlayerStat[]): string[] {
  return starters.map(slotOf);
}

interface FlowEdge {
  to: number;
  cap: number;
  cost: number;
}

/**
 * Min-cost flow that only augments **improving** paths (negative marginal cost),
 * yielding a maximum-weight bipartite matching rather than a forced max-cardinality
 * one — so a slot whose only eligible players score negative is left empty (0)
 * rather than filled at a loss, matching real "best legal lineup" semantics.
 */
class MinCostMatcher {
  private edges: FlowEdge[] = [];
  private adj: number[][];
  private n: number;

  constructor(n: number) {
    this.n = n;
    this.adj = Array.from({ length: n }, () => []);
  }

  /** Add a directed edge (plus its residual reverse) and return the forward index. */
  addEdge(u: number, v: number, cap: number, cost: number): number {
    const forward = this.edges.length;
    this.adj[u].push(forward);
    this.edges.push({ to: v, cap, cost });
    this.adj[v].push(this.edges.length);
    this.edges.push({ to: u, cap: 0, cost: -cost });
    return forward;
  }

  /** Run successive shortest (cheapest) augmenting paths while they improve. */
  solve(source: number, sink: number): void {
    for (;;) {
      const dist = new Array<number>(this.n).fill(Infinity);
      const inQueue = new Array<boolean>(this.n).fill(false);
      const prevEdge = new Array<number>(this.n).fill(-1);
      dist[source] = 0;
      const queue = [source];
      inQueue[source] = true;
      // SPFA (Bellman-Ford queue variant) handles the negative edge costs.
      while (queue.length) {
        const u = queue.shift()!;
        inQueue[u] = false;
        for (const ei of this.adj[u]) {
          const e = this.edges[ei];
          if (e.cap > 0 && dist[u] + e.cost < dist[e.to]) {
            dist[e.to] = dist[u] + e.cost;
            prevEdge[e.to] = ei;
            if (!inQueue[e.to]) {
              inQueue[e.to] = true;
              queue.push(e.to);
            }
          }
        }
      }
      // Stop once the cheapest augmenting path no longer lowers total cost.
      if (dist[sink] >= 0 || dist[sink] === Infinity) break;
      // Every source→slot edge has capacity 1, so each path carries one unit.
      let v = sink;
      while (v !== source) {
        const ei = prevEdge[v];
        this.edges[ei].cap -= 1;
        this.edges[ei ^ 1].cap += 1;
        v = this.edges[ei ^ 1].to;
      }
    }
  }

  /** A forward `slot→player` edge is used iff its residual capacity is exhausted. */
  isUsed(edgeIndex: number): boolean {
    return this.edges[edgeIndex].cap === 0;
  }
}

export interface OptimalLineup {
  optimalPoints: number;
  /** Map from slot index (into `deriveRequiredSlots`) to the player that fills it. */
  assignment: Map<number, PlayerStat>;
}

/**
 * The maximum-points legal starting lineup from the `starters + bench` pool,
 * respecting the slot template derived from the starters. Exact (not greedy):
 * solved as a max-weight bipartite matching of slots↔players via min-cost flow.
 */
export function optimalLineup(
  starters: PlayerStat[],
  bench: PlayerStat[],
): OptimalLineup {
  const slots = deriveRequiredSlots(starters);
  const pool = [...starters, ...bench];
  const slotCount = slots.length;
  const playerCount = pool.length;

  // Node layout: 0 = source, [1..slotCount] = slots,
  // [slotCount+1 .. slotCount+playerCount] = players, last = sink.
  const source = 0;
  const slotNode = (i: number) => 1 + i;
  const playerNode = (j: number) => 1 + slotCount + j;
  const sink = 1 + slotCount + playerCount;
  const matcher = new MinCostMatcher(sink + 1);

  // Track each slot's eligible forward edges (and which player they reach) so we
  // can read the assignment back off the saturated edges after solving.
  const slotEdges: { edgeIndex: number; playerIndex: number }[][] = Array.from(
    { length: slotCount },
    () => [],
  );

  for (let i = 0; i < slotCount; i++) {
    matcher.addEdge(source, slotNode(i), 1, 0);
    const eligible = eligiblePositions(slots[i]);
    for (let j = 0; j < playerCount; j++) {
      if (eligible.has(normalize(pool[j].position))) {
        // Scaled integer cost = −points keeps the SPFA relaxation float-stable.
        const edgeIndex = matcher.addEdge(
          slotNode(i),
          playerNode(j),
          1,
          -Math.round(points(pool[j]) * 100),
        );
        slotEdges[i].push({ edgeIndex, playerIndex: j });
      }
    }
  }
  for (let j = 0; j < playerCount; j++) {
    matcher.addEdge(playerNode(j), sink, 1, 0);
  }

  matcher.solve(source, sink);

  const assignment = new Map<number, PlayerStat>();
  let optimalPoints = 0;
  for (let i = 0; i < slotCount; i++) {
    for (const { edgeIndex, playerIndex } of slotEdges[i]) {
      if (matcher.isUsed(edgeIndex)) {
        assignment.set(i, pool[playerIndex]);
        // Read points back from the original float, not the scaled cost.
        optimalPoints += points(pool[playerIndex]);
        break;
      }
    }
  }

  return { optimalPoints, assignment };
}

export interface SlotRow {
  slot: string;
  started: { name: string; points: number } | null;
  optimal: { name: string; points: number } | null;
  /** optimal − started for this slot; positive marks a suboptimal (changed) slot. */
  delta: number;
}

export interface StartSitReport {
  /** False when the bench is empty (ESPN seasons before 2018) — efficiency can't be measured. */
  hasBenchData: boolean;
  actualPoints: number;
  optimalPoints: number;
  /** optimalPoints − actualPoints, never negative. */
  pointsLeft: number;
  /** actualPoints / optimalPoints in [0, 1]; 1 when optimalPoints is 0. */
  efficiencyPct: number;
  /** One row per slot instance; rows with a positive delta are the start/sit mistakes. */
  rows: SlotRow[];
}

/** Deterministic ordering: points desc, then player_id asc. */
function byPointsDesc(a: PlayerStat, b: PlayerStat): number {
  return points(b) - points(a) || a.player_id - b.player_id;
}

/**
 * Per-side start/sit report comparing the actual starting lineup to the optimal
 * one, broken down slot-by-slot. Rows are built by aligning, within each slot
 * label, the actual starters and the optimal players (both sorted best-first), so
 * the per-row deltas sum exactly to `pointsLeft`.
 */
export function computeStartSitReport(
  starters: PlayerStat[],
  bench: PlayerStat[],
): StartSitReport {
  const actualPoints = starters.reduce((sum, p) => sum + points(p), 0);
  const { optimalPoints, assignment } = optimalLineup(starters, bench);
  const slots = deriveRequiredSlots(starters);

  // Group actual starters and optimal players by slot label.
  const actualByLabel = new Map<string, PlayerStat[]>();
  for (const s of starters) {
    const label = slotOf(s);
    (actualByLabel.get(label) ?? actualByLabel.set(label, []).get(label)!).push(
      s,
    );
  }
  const optimalByLabel = new Map<string, PlayerStat[]>();
  for (const [slotIndex, player] of assignment) {
    const label = slots[slotIndex];
    (
      optimalByLabel.get(label) ?? optimalByLabel.set(label, []).get(label)!
    ).push(player);
  }

  const rows: SlotRow[] = [];
  // Preserve a stable label order (the order slots first appear among starters).
  const seen = new Set<string>();
  for (const label of slots) {
    if (seen.has(label)) continue;
    seen.add(label);
    const actual = (actualByLabel.get(label) ?? []).slice().sort(byPointsDesc);
    const optimal = (optimalByLabel.get(label) ?? [])
      .slice()
      .sort(byPointsDesc);
    const count = Math.max(actual.length, optimal.length);
    for (let k = 0; k < count; k++) {
      const a = actual[k] ?? null;
      const o = optimal[k] ?? null;
      rows.push({
        slot: label,
        started: a ? { name: a.full_name, points: points(a) } : null,
        optimal: o ? { name: o.full_name, points: points(o) } : null,
        delta: (o ? points(o) : 0) - (a ? points(a) : 0),
      });
    }
  }

  const efficiencyPct =
    optimalPoints <= 0
      ? 1
      : Math.max(0, Math.min(1, actualPoints / optimalPoints));

  return {
    hasBenchData: bench.length > 0,
    actualPoints,
    optimalPoints,
    pointsLeft: Math.max(0, optimalPoints - actualPoints),
    efficiencyPct,
    rows,
  };
}
