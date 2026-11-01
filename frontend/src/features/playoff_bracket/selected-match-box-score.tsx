import { type BracketMatch, type Matchup } from './api-calls';

import type { Platform } from '@/components/api/types';
import { BoxScoreCard } from '@/components/box-score-card';
import { getTeamColor } from '@/features/playoff_bracket/team';

export function SelectedMatchBoxScore({
  selectedMatch,
  selectedMatchupData,
  platform,
  onClose,
}: {
  selectedMatch: BracketMatch;
  selectedMatchupData: Matchup;
  platform: Platform;
  onClose: () => void;
}) {
  return (
    <BoxScoreCard
      left={{
        teamLogo: selectedMatch.team_1_team_logo,
        teamName:
          selectedMatch.team_1_team_name ||
          `Team ${selectedMatch.team_1_display_name}`,
        ownerUsername: selectedMatch.team_1_display_name,
        color: getTeamColor(selectedMatch.team_1_id),
        score: selectedMatch.team_1_score ?? 0,
        starters:
          selectedMatchupData.team_a_id === selectedMatch.team_1_id
            ? selectedMatchupData.team_a_starters
            : selectedMatchupData.team_b_starters,
        bench:
          selectedMatchupData.team_a_id === selectedMatch.team_1_id
            ? selectedMatchupData.team_a_bench
            : selectedMatchupData.team_b_bench,
        isWinner: selectedMatch.winner === selectedMatch.team_1_id,
      }}
      right={{
        teamLogo: selectedMatch.team_2_team_logo,
        teamName:
          selectedMatch.team_2_team_name ||
          `Team ${selectedMatch.team_2_display_name}`,
        ownerUsername: selectedMatch.team_2_display_name,
        color: getTeamColor(selectedMatch.team_2_id),
        score: selectedMatch.team_2_score ?? 0,
        starters:
          selectedMatchupData.team_a_id === selectedMatch.team_2_id
            ? selectedMatchupData.team_a_starters
            : selectedMatchupData.team_b_starters,
        bench:
          selectedMatchupData.team_a_id === selectedMatch.team_2_id
            ? selectedMatchupData.team_a_bench
            : selectedMatchupData.team_b_bench,
        isWinner: selectedMatch.winner === selectedMatch.team_2_id,
      }}
      platform={platform}
      season={selectedMatch.season}
      onClose={onClose}
    />
  );
}
