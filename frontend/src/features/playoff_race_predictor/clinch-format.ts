import { type ClinchScenario, type TieMargin } from './compute-projection';

/** A team's display label: its fantasy team name, falling back to the owner. */
export function teamLabel(team: {
  teamName: string;
  ownerUsername: string;
}): string {
  return team.teamName || team.ownerUsername;
}

/**
 * Summarizes the points-for tiebreak by its tightest margin — the one that could flip:
 * "Wolves leads by 49", or "Wolves trails Hawks by 15" when the team is behind a rival.
 */
export function marginSummary(
  team: { teamName: string; ownerUsername: string },
  margins: TieMargin[],
): string {
  const tightest = margins.reduce((a, b) => (b.gap < a.gap ? b : a));
  const gap = Math.round(Math.abs(tightest.gap));
  return tightest.gap >= 0
    ? `${teamLabel(team)} leads by ${gap}`
    : `${teamLabel(team)} trails ${teamLabel(tightest.rival)} by ${gap}`;
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
