import { type ClinchScenario, type TieMargin } from './compute-projection';

/** A team's display label: its fantasy team name, falling back to the owner. */
export function teamLabel(team: {
  teamName: string;
  ownerUsername: string;
}): string {
  return team.teamName || team.ownerUsername;
}

/** "leads Rams by 30, trails Hawks by 15" — describes the points-for tiebreak. */
export function marginList(margins: TieMargin[]): string {
  return margins
    .map(
      (m) =>
        `${m.gap >= 0 ? 'leads' : 'trails'} ${teamLabel(m.rival)} by ${Math.round(
          Math.abs(m.gap),
        )}`,
    )
    .join(', ');
}

export const CLINCH_PILL: Record<
  ClinchScenario['category'],
  { label: string; cls: string }
> = {
  'win-and-in': {
    label: 'Win & in',
    cls: 'bg-primary/10 text-primary',
  },
  'controls-destiny': {
    label: 'Controls destiny',
    cls: 'bg-primary/10 text-primary',
  },
  'must-win': {
    label: 'Must win',
    cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
};
