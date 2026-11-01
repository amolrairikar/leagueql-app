import { type StatDef } from '@/features/manager_comparison/types';

export const STAT_DEFS: StatDef[] = [
  {
    key: 'h2hWins',
    label: 'H2H Wins',
    value: (m) => m.stats.h2hWins,
    fmt: (m) => String(m.stats.h2hWins),
    higher: true,
  },
  {
    key: 'longestStreak',
    label: 'Longest Streak',
    value: (m) => m.stats.longestStreak,
    fmt: (m) => String(m.stats.longestStreak),
    higher: true,
  },
  {
    key: 'championships',
    label: 'Championships',
    value: (m) => m.stats.championships,
    fmt: (m) => String(m.stats.championships),
    higher: true,
  },
  {
    key: 'playoffApps',
    label: 'Playoff Apps',
    value: (m) => m.stats.playoffApps,
    fmt: (m) => String(m.stats.playoffApps),
    higher: true,
  },
  {
    key: 'record',
    label: 'Record',
    value: (m) => m.stats.winPct,
    fmt: (m) =>
      `${m.stats.wins}-${m.stats.losses}-${m.stats.ties} (.${Math.round(
        m.stats.winPct * 1000,
      )
        .toString()
        .padStart(3, '0')})`,
    higher: true,
  },
  {
    key: 'avgPf',
    label: 'Avg PF',
    value: (m) => m.stats.avgPf,
    fmt: (m) => m.stats.avgPf.toFixed(1),
    higher: true,
  },
  {
    key: 'highScore',
    label: 'High Score',
    value: (m) => m.stats.highScore,
    fmt: (m) => m.stats.highScore.toFixed(1),
    higher: true,
  },
];
