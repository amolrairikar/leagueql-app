import { type MatchupItem } from '@/features/manager_comparison/api-calls';

export interface Manager {
  name: string;
  team: string;
  color: string;
  init: string;
  ownerId: string;
  stats: {
    wins: number;
    losses: number;
    ties: number;
    avgPf: number;
    highScore: number;
    winPct: number;
    h2hWins: number;
    longestStreak: number;
    playoffApps: number;
    championships: number;
  };
}

export interface GameLog {
  week: string;
  season: string;
  lp: number;
  rp: number;
  matchupItem: MatchupItem;
  leftIsA: boolean;
}

export interface StatDef {
  key: string;
  label: string;
  value: (m: Manager) => number;
  fmt: (m: Manager) => string;
  higher: boolean;
}
