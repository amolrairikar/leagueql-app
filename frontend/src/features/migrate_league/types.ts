import type { Platform } from '@/components/api/types';
import {
  type EspnMemberEntry,
  type SleeperUserEntry,
  type YahooMemberEntry,
} from '@/features/migrate_league/api-calls';

export type WizardStep = 1 | 2 | 3 | 4 | 5;

export interface NewPlatformInfo {
  newPlatform: Platform;
  newPlatformLeagueId: string;
  season?: string;
  s2?: string;
  swid?: string;
}

export type NewPlatformUser =
  EspnMemberEntry | SleeperUserEntry | YahooMemberEntry;
