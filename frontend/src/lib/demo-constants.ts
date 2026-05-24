/**
 * Demo mode configuration constants.
 * Provides a single source of truth for demo league settings.
 *
 * The demo league started on ESPN (2022–2024) and migrated to Sleeper for 2025.
 * Post-migration, the active league ID and platform reflect the Sleeper league.
 */

/** Original ESPN league ID (2022–2024 seasons). */
export const DEMO_ESPN_LEAGUE_ID = '999999999';

/** Sleeper league ID used after the demo migration (2025 season). */
export const DEMO_SLEEPER_LEAGUE_ID = '888888888';

/**
 * Active league ID for demo mode — the Sleeper ID post-migration.
 */
export const DEMO_LEAGUE_ID = DEMO_SLEEPER_LEAGUE_ID;

/**
 * Active platform for demo mode — Sleeper post-migration.
 */
export const DEMO_PLATFORM = 'SLEEPER' as const;

/**
 * All seasons in the demo dataset across both platforms.
 */
export const DEMO_SEASONS = ['2022', '2023', '2024', '2025'];
