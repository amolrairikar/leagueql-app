import { type SeasonStandingsItem } from '@/features/season_standings/api-calls';
import {
  type MatchupItem,
  type TransactionItem,
} from '@/features/transactions/api-calls';
import { type Result } from '@/lib/result';

export type TransactionsResult = Result<TransactionItem[]>;

export type StandingsResult = Result<SeasonStandingsItem[]>;

export type MatchupsResult = Result<MatchupItem[]>;

export type TypeFilter = 'trade' | 'waiver' | 'free_agent';

export const TYPE_FILTERS: { value: TypeFilter; label: string }[] = [
  { value: 'trade', label: 'Trades' },
  { value: 'waiver', label: 'Waivers' },
  { value: 'free_agent', label: 'Free Agents' },
];
