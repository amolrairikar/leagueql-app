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
  TQB: 1,
  OP: 2,
  RB: 3,
  'RB/WR': 4,
  WR: 5,
  'WR/TE': 6,
  TE: 7,
  FLEX: 8,
  'D/ST': 9,
  K: 10,
  // IDP and other defensive / special slots, displayed after offense
  DL: 11,
  DE: 12,
  DT: 13,
  EDR: 14,
  LB: 15,
  DB: 16,
  CB: 17,
  S: 18,
  DP: 19,
  P: 20,
  HC: 21,
};
