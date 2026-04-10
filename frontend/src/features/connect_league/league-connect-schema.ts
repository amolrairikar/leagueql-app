import { z } from 'zod';

export const Platform = z.enum(['espn', 'sleeper']);

export const leagueConnectSchema = z.discriminatedUnion('platform', [
  z.object({
    platform: z.literal('espn'),
    leagueId: z.string().min(1, 'League ID is required'),
    latestSeason: z.string().min(1, 'Latest season is required'),
    swid: z.string().min(1, 'SWID is required'),
    espnS2: z.string().min(1, 'ESPN_S2 is required'),
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
