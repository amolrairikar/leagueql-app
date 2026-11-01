import { type DraftPickItem } from './api-calls';

export interface BustWithAlts {
  pick: DraftPickItem;
  alts: DraftPickItem[];
  bustKey: string;
}
