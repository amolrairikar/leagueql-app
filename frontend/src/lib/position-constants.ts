/**
 * Position normalization constants.
 * Provides a single source of truth for normalizing position abbreviations
 * across different fantasy platforms (e.g., ESPN uses 'D/ST', Sleeper uses 'DEF').
 */

/**
 * Maps platform-specific position abbreviations to a normalized form.
 * Currently handles the ESPN 'D/ST' → 'DEF' normalization.
 */
export const POS_NORMALIZE: Record<string, string> = {
  'D/ST': 'DEF',
};

/**
 * Fantasy position ordering for display purposes.
 * Lower values appear first in sorted lists.
 */
export const FANTASY_POSITION_ORDER: Record<string, number> = {
  QB: 0,
  RB: 1,
  WR: 2,
  TE: 3,
  FLEX: 4,
  'D/ST': 5,
  K: 6,
};
