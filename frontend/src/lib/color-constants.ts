/**
 * Color constants for the application.
 * Provides a single source of truth for all hardcoded color values.
 */

// ── Position Colors ─────────────────────────────────────────────────────────────

export interface PositionColorMeta {
  color: string;
  bg: string;
  tc: string;
  label: string;
}

// `color` is the vivid accent (chart fills, strokes, icons); `bg`/`tc` are the
// light badge background + text. The accents are tuned to be mutually distinct
// (e.g. QB indigo vs DEF sky-blue) so they read well even as adjacent segments
// in the positional-scoring stacked bars; the light `bg`/`tc` tints are left as
// the established badge colors used by the draft boards and other features.
export const POSITION_COLORS: Record<string, PositionColorMeta> = {
  QB: { color: '#4f46e5', bg: '#EEEDFE', tc: '#3C3489', label: 'Quarterbacks' },
  WR: {
    color: '#ea580c',
    bg: '#FAECE7',
    tc: '#712B13',
    label: 'Wide receivers',
  },
  RB: {
    color: '#059669',
    bg: '#E1F5EE',
    tc: '#085041',
    label: 'Running backs',
  },
  TE: { color: '#db2777', bg: '#FCE7F0', tc: '#9D174D', label: 'Tight ends' },
  DEF: { color: '#0284c7', bg: '#E6F1FB', tc: '#0C447C', label: 'Defenses' },
  K: { color: '#64748b', bg: '#F1EFE8', tc: '#444441', label: 'Kickers' },
};

/**
 * Shared position → color lookup so every feature (draft boards, analytics
 * charts) renders a position in the same hue. Accepts either the platform
 * `D/ST` label or the normalized `DEF`; unknown positions fall back to the
 * kicker palette, matching the draft boards.
 */
export function positionColorMeta(position: string): PositionColorMeta {
  const key = position === 'D/ST' ? 'DEF' : position;
  return POSITION_COLORS[key] ?? POSITION_COLORS.K;
}

// ── Avatar Colors ───────────────────────────────────────────────────────────────

export const AVATAR_COLORS = [
  '#4338ca',
  '#0f6e56',
  '#993c1d',
  '#993556',
  '#185FA5',
  '#854F0B',
  '#5F5E5A',
  '#A32D2D',
  '#7c3aed',
  '#b45309',
  '#0891b2',
  '#be185d',
  '#1d6f6f',
  '#6b4f9c',
] as const;

/** Stable avatar color for a 0-based index, cycling through {@link AVATAR_COLORS}. */
export function avatarColor(index: number): string {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

// ── UI Status Colors ───────────────────────────────────────────────────────────

export const UI_COLORS = {
  // Winner badge
  winner: {
    bg: '#EAF3DE',
    text: '#27500A',
  },
  // Champion
  champion: {
    border: '#534AB7',
    bg: '#EEEDFE',
    text: '#3C3489',
  },
  // Gold (for rankings/records)
  gold: '#EF9F27',
  // Default fallback color
  default: '#6b7280',
  // Positive/negative indicators
  positive: '#27500A',
  negative: '#791F1F',
} as const;

// ── Record Type Colors ─────────────────────────────────────────────────────────

export const RECORD_COLORS = {
  highestTeamScore: '#4338ca',
  lowestTeamScore: '#993c1d',
  highestMatchupScore: '#0f6e56',
  lowestMatchupScore: '#BA7517',
  biggestBlowout: '#185FA5',
  closestGame: '#5F5E5A',
} as const;

// ── Browser Chrome Colors (macOS window buttons) ─────────────────────────────

export const BROWSER_CHROME_COLORS = {
  red: '#FF5F57',
  yellow: '#FFBD2E',
  green: '#28C840',
} as const;

// ── Matchup Status Colors ─────────────────────────────────────────────────────

export const MATCHUP_STATUS_COLORS = {
  selected: {
    border: '#4338ca',
  },
  pending: {
    bg: '#f1f5f9',
    text: '#64748b',
  },
  completed: {
    bg: '#fef3c7',
    text: '#92400e',
  },
  // Winners consolation bracket (ESPN WINNERS_CONSOLATION_LADDER)
  consolation: {
    bg: '#DBEAFE',
    text: '#1E40AF',
  },
} as const;

// ── Nemesis Color (for manager history) ─────────────────────────────────────────

export const NEMESIS_COLORS = {
  bg: '#FCEBEB',
  text: '#791F1F',
  accent: '#E24B4A',
} as const;
