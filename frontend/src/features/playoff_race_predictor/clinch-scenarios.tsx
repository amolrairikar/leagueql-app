import { useMemo, type ReactNode } from 'react';

import {
  computeClinchScenarios,
  type ClinchScenario,
  type Picks,
  type PredictorModel,
} from './compute-projection';

import { TeamAvatar } from '@/components/team-avatar';
import {
  CLINCH_PILL,
  marginList,
  teamLabel,
} from '@/features/playoff_race_predictor/clinch-format';
import { avatarColor } from '@/lib/color-constants';
import { cn } from '@/lib/utils';

/**
 * Clinching scenarios: for teams still in contention, whether their next un-picked
 * game clinches ("win & in") or eliminates ("must win") them — or both ("controls its
 * own destiny") — with the points-for margin for any seat that could come down to a
 * same-record tie. Hidden when nothing is decisive. See {@link computeClinchScenarios}.
 */
export function ClinchScenarios({
  model,
  picks,
  colorByTeam,
}: {
  model: PredictorModel;
  picks: Picks;
  colorByTeam: Map<string, string>;
}) {
  const result = useMemo(
    () => computeClinchScenarios(model, picks),
    [model, picks],
  );
  if (!result) return null;

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden mt-5">
      <div className="flex items-center justify-between gap-2 px-4 pt-3.5 pb-1">
        <span className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          Clinching scenarios
        </span>
      </div>
      <ul className="flex flex-col p-1.5">
        {result.scenarios.map((s) => (
          <ClinchRow
            key={s.team.teamId}
            scenario={s}
            color={colorByTeam.get(s.team.teamId) ?? avatarColor(0)}
          />
        ))}
      </ul>
      {result.numPlayoffTeamsAssumed && (
        <div className="px-4 py-2.5 border-t border-border/50 text-[11px] text-muted-foreground">
          Assumes {result.numPlayoffTeams} playoff teams.
        </div>
      )}
    </div>
  );
}

export function ClinchRow({
  scenario,
  color,
}: {
  scenario: ClinchScenario;
  color: string;
}) {
  const { team, category, opponent, tieMargins } = scenario;
  const pill = CLINCH_PILL[category];
  const oppName = opponent ? teamLabel(opponent) : null;

  let text: ReactNode;
  if (category === 'controls-destiny') {
    text = (
      <>
        <span className="text-foreground font-medium">
          Controls its own destiny
        </span>{' '}
        — win to clinch, out with a loss
      </>
    );
  } else if (category === 'win-and-in') {
    text = (
      <>
        <span className="text-foreground font-medium">Clinches with a win</span>
        {oppName ? ` over ${oppName}` : ''}
        {tieMargins.length > 0 && (
          <>
            {' '}
            — on a loss, the last seat is on points-for (
            {marginList(tieMargins)})
          </>
        )}
      </>
    );
  } else {
    text = (
      <>
        <span className="text-foreground font-medium">
          Must {oppName ? `beat ${oppName}` : 'win'}
        </span>{' '}
        to stay alive
        {tieMargins.length > 0 && (
          <> — then take the points-for tiebreak ({marginList(tieMargins)})</>
        )}
      </>
    );
  }

  return (
    <li className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-muted">
      <div className="flex items-center gap-2 min-w-0">
        <TeamAvatar
          teamLogo={team.teamLogo}
          teamName={team.teamName}
          ownerUsername={team.ownerUsername}
          color={color}
        />
        <span className="text-[13px] font-semibold truncate">
          {team.ownerUsername}
        </span>
      </div>
      <span className="text-[12.5px] text-muted-foreground min-w-0">
        {text}
      </span>
      <span
        className={cn(
          'text-[10px] font-bold uppercase tracking-[0.03em] px-2 py-0.5 rounded-full whitespace-nowrap',
          pill.cls,
        )}
      >
        {pill.label}
      </span>
    </li>
  );
}
