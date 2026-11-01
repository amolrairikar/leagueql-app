import { Check } from 'lucide-react';

import {
  recordEnteringWeek,
  type PickableMatchup,
  type Picks,
  type PredictorModel,
} from './compute-projection';

import { TeamAvatar } from '@/components/team-avatar';
import { avatarColor } from '@/lib/color-constants';
import { cn } from '@/lib/utils';

export function MatchupRow({
  matchup,
  model,
  picks,
  colorByTeam,
  onPick,
}: {
  matchup: PickableMatchup;
  model: PredictorModel;
  picks: Picks;
  colorByTeam: Map<string, string>;
  onPick: (m: PickableMatchup, teamId: string) => void;
}) {
  const pick = picks[matchup.key];
  return (
    <div className="grid grid-cols-[1fr_40px_1fr] items-stretch">
      <TeamCard
        teamId={matchup.teamAId}
        matchup={matchup}
        model={model}
        picks={picks}
        state={pick ? (pick === matchup.teamAId ? 'win' : 'lose') : 'none'}
        color={colorByTeam.get(matchup.teamAId) ?? avatarColor(0)}
        onPick={onPick}
      />
      <div className="grid place-items-center text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        vs
      </div>
      <TeamCard
        teamId={matchup.teamBId}
        matchup={matchup}
        model={model}
        picks={picks}
        state={pick ? (pick === matchup.teamBId ? 'win' : 'lose') : 'none'}
        color={colorByTeam.get(matchup.teamBId) ?? avatarColor(0)}
        onPick={onPick}
      />
    </div>
  );
}

export function TeamCard({
  teamId,
  matchup,
  model,
  picks,
  state,
  color,
  onPick,
}: {
  teamId: string;
  matchup: PickableMatchup;
  model: PredictorModel;
  picks: Picks;
  state: 'win' | 'lose' | 'none';
  color: string;
  onPick: (m: PickableMatchup, teamId: string) => void;
}) {
  const team = model.teams.get(teamId)!;
  const rec = recordEnteringWeek(model, teamId, matchup.week, picks);
  return (
    <button
      type="button"
      onClick={() => onPick(matchup, teamId)}
      className={cn(
        'flex items-center gap-2.5 px-3.5 py-2.5 rounded-[10px] border w-full text-left transition-colors cursor-pointer',
        state === 'win' && 'border-primary bg-primary/10',
        state === 'lose' && 'opacity-50 border-border',
        state === 'none' && 'border-border bg-card hover:border-ring',
      )}
    >
      <TeamAvatar
        teamLogo={team.teamLogo}
        teamName={team.teamName}
        ownerUsername={team.ownerUsername}
        color={color}
      />
      <div className="flex flex-col min-w-0">
        <span className="text-[13px] font-medium truncate">
          {team.ownerUsername}
        </span>
        <span className="text-[11px] text-muted-foreground truncate">
          {team.teamName || `Team ${team.ownerUsername}`}
        </span>
      </div>
      <span className="ml-auto text-[12px] tabular-nums text-muted-foreground">
        {rec.wins}-{rec.losses}
        {rec.ties > 0 ? `-${rec.ties}` : ''}
      </span>
      {state === 'win' && <Check className="w-4 h-4 text-primary shrink-0" />}
    </button>
  );
}
