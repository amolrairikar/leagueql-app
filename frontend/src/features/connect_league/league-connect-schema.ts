import { z } from 'zod';

export const Platform = z.enum(['espn', 'sleeper']);

export const leagueConnectSchema = z.discriminatedUnion('platform', [
  z.object({
    platform: z.literal('espn'),
    leagueId: z.string().min(1, 'League ID is required'),
    latestSeason: z
      .string()
      .min(1, 'Latest season is required')
      .regex(/^\d{4}$/, 'Latest season must be a 4-digit number (e.g. 2026)'),
    swid: z.string().min(1, 'SWID is required'),
    espnS2: z.string().min(1, 'ESPN_S2 is required'),
    // Opt into scheduled weekly auto-refresh (backend/scheduled-league-auto-refresh).
    // Optional/off by default (opt-in); when on, the ESPN cookies are stored encrypted
    // for reuse. Kept optional (not .default) so the resolver's input/output types match.
    autoRefresh: z.boolean().optional(),
  }),
  z.object({
    platform: z.literal('sleeper'),
    leagueId: z.string().min(1, 'League ID is required'),
  }),
]);

export type LeagueConnectFormValues = z.infer<typeof leagueConnectSchema>;

export type EspnFormValues = Extract<
  LeagueConnectFormValues,
  { platform: 'espn' }
>;
