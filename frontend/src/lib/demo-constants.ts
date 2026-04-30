/**
 * Demo mode configuration constants.
 * Provides a single source of truth for demo league settings.
 */

/**
 * League ID used for demo mode.
 * This ID is used to identify the demo league across the application.
 */
export const DEMO_LEAGUE_ID = '999999999';

/**
 * Platform used for demo mode.
 */
export const DEMO_PLATFORM = 'ESPN' as const;

/**
 * Seasons available in the demo dataset.
 * When the demo dataset changes or new seasons are added, update this array.
 */
export const DEMO_SEASONS = ['2022', '2023', '2024'];
