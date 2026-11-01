import { Trophy } from 'lucide-react';

import { type BracketMatch } from './api-calls';

import { getTeamColor } from '@/features/playoff_bracket/team';
import type { Team } from '@/features/playoff_bracket/team';
import { UI_COLORS } from '@/lib/color-constants';

export function TeamRow({
  team,
  score,
  isWinner,
  played,
  isBye,
  record,
  isChampion,
}: {
  team: Team | null;
  score: number | null;
  isWinner: boolean;
  played: boolean;
  isBye: boolean;
  record?: string | null;
  isChampion?: boolean;
}) {
  if (!team) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-border/30 last:border-b-0 opacity-55">
        <span className="text-[10px] font-medium text-muted-foreground w-3 text-center">
          —
        </span>
        <div className="w-5.5 h-5.5 rounded-full bg-border/50 flex items-center justify-center shrink-0" />
        <span className="text-[12px] font-medium text-muted-foreground italic flex-1 truncate">
          TBD
        </span>
      </div>
    );
  }

  const color = getTeamColor(team.team_id);
  const init = team.display_name.slice(0, 2).toUpperCase();
  const rowClass = played
    ? isWinner
      ? 'bg-muted'
      : 'opacity-40'
    : isBye
      ? 'opacity-55'
      : '';

  const scoreHtml = isBye ? (
    <span
      className="text-[9px] font-medium uppercase tracking-[0.05em] px-1 py-0.5 rounded"
      style={{
        color: UI_COLORS.champion.text,
        background: UI_COLORS.champion.bg,
      }}
    >
      BYE
    </span>
  ) : played && score !== null ? (
    <span
      className={`text-[12px] font-medium tabular-nums ${isWinner ? 'text-foreground' : 'text-muted-foreground'}`}
    >
      {Number(score).toFixed(1)}
    </span>
  ) : (
    <span className="text-[10px] font-medium text-muted-foreground italic">
      TBD
    </span>
  );

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1.5 border-b border-border/30 last:border-b-0 ${rowClass}`}
    >
      <div
        className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[8px] font-medium text-white shrink-0"
        style={{ background: color }}
      >
        {init}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium text-foreground truncate">
            {team.display_name}
          </span>
          {isChampion && (
            <Trophy className="h-3.5 w-3.5 shrink-0 text-yellow-500 fill-yellow-500" />
          )}
        </div>
        <div className="text-[10px] text-muted-foreground truncate">
          {team.team_name || `Team ${team.display_name}`}
          {record ? ` (${record})` : ''}
        </div>
      </div>
      {scoreHtml}
    </div>
  );
}

export function MatchupCard({
  match,
  extraClass,
  extraStyle,
  played,
  onClick,
  record1,
  record2,
  championId,
}: {
  match: BracketMatch | null;
  extraClass?: string;
  extraStyle?: React.CSSProperties;
  played: boolean;
  onClick?: () => void;
  record1?: string | null;
  record2?: string | null;
  championId?: string | null;
}) {
  if (!match) {
    return (
      <div className="bg-transparent border border-dashed border-border/30 rounded-md flex items-center justify-center p-3">
        <span className="text-[10px] text-muted-foreground italic">
          bye week
        </span>
      </div>
    );
  }

  const team1: Team = {
    team_id: match.team_1_id,
    display_name: match.team_1_display_name,
    team_name: match.team_1_team_name,
    team_logo: match.team_1_team_logo,
  };
  const team2: Team = {
    team_id: match.team_2_id,
    display_name: match.team_2_display_name,
    team_name: match.team_2_team_name,
    team_logo: match.team_2_team_logo,
  };

  const aWins = match.winner === match.team_1_id;
  const score1 = match.team_1_score ?? null;
  const score2 = match.team_2_score ?? null;

  return (
    <div
      className={`bg-card border border-border/30 rounded-md overflow-hidden ${extraClass ?? ''} ${onClick ? 'cursor-pointer hover:border-border/60' : ''}`}
      style={extraStyle}
      onClick={onClick}
    >
      <TeamRow
        team={team1}
        score={score1}
        isWinner={played && aWins}
        played={played}
        isBye={false}
        record={record1}
        isChampion={championId === team1.team_id}
      />
      <TeamRow
        team={team2}
        score={score2}
        isWinner={played && !aWins}
        played={played}
        isBye={false}
        record={record2}
        isChampion={championId === team2.team_id}
      />
    </div>
  );
}

export function ByeCard({ team }: { team: Team }) {
  const color = getTeamColor(team.team_id);
  const init = team.display_name.slice(0, 2).toUpperCase();

  return (
    <div className="bg-card border border-border/30 rounded-md overflow-hidden opacity-70">
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <div
          className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[8px] font-medium text-white shrink-0"
          style={{ background: color }}
        >
          {init}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-medium text-foreground truncate">
            {team.display_name}
          </div>
          <div className="text-[10px] text-muted-foreground truncate">
            {team.team_name || `Team ${team.display_name}`}
          </div>
        </div>
        <span
          className="text-[9px] font-medium uppercase tracking-[0.05em] px-1 py-0.5 rounded"
          style={{
            color: UI_COLORS.champion.text,
            background: UI_COLORS.champion.bg,
          }}
        >
          BYE
        </span>
      </div>
    </div>
  );
}
