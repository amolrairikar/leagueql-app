import { z } from 'zod';

export const Platform = z.enum(['espn', 'sleeper']);

export const leagueConnectSchema = z.discriminatedUnion('platform', [
  z.object({
    platform: z.literal('espn'),
    leagueId: z.string().min(1, 'League ID is required'),
    latestSeason: z.string().min(1, 'Latest season is required'),
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
