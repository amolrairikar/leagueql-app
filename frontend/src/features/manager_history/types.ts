import { type PlayerStat } from '@/components/box-score-card';
import { type Result } from '@/lib/result';

export interface RawBoxScoreSide {
  ownerId: string;
  teamLogo: string | null;
  teamName: string;
  ownerUsername: string;
  score: number;
  starters: PlayerStat[];
  bench: PlayerStat[];
  isWinner: boolean;
}

export type BoxScoreSideData = RawBoxScoreSide & { color: string };

export interface RawScheduleGame {
  week: number;
  result: 'W' | 'L' | 'T';
  isPostseason: boolean;
  own: RawBoxScoreSide;
  opp: RawBoxScoreSide;
}

export interface ScheduleGame {
  week: number;
  result: 'W' | 'L' | 'T';
  isPostseason: boolean;
  own: BoxScoreSideData;
  opp: BoxScoreSideData;
}

export interface SeasonEntry {
  year: string;
  team: string;
  record: string;
  pts: number;
  avg: number;
  high: number;
  /** Playoff outcome; null for an in-progress season (not settled yet). */
  result: 'champion' | 'runner' | 'playoff' | 'elim' | null;
  finish: number | null;
  schedule: ScheduleGame[];
}

export interface RivalryEntry {
  oppId: string;
  oppName: string;
  oppTeam: string;
  oppColor: string;
  oppInit: string;
  w: number;
  l: number;
  avgFor: number;
  avgAgainst: number;
  lastResult: 'W' | 'L';
}

export interface ManagerData {
  owner_id: string;
  owner_username: string;
  init: string;
  color: string;
  currentTeam: string;
  allTime: {
    wins: number;
    losses: number;
    championships: number;
    playoffs: number;
    highScore: number;
    avgPts: number;
  };
  seasons: SeasonEntry[];
  rivalries: RivalryEntry[];
}

export type DataResult = Result<ManagerData[]>;

export interface RivalryAcc {
  w: number;
  l: number;
  totalFor: number;
  totalAgainst: number;
  count: number;
  lastSeason: string;
  lastWeek: number;
  lastWon: boolean;
}

// ── Constants ─────────────────────────────────────────────────────────────────
