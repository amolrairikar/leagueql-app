import { type BracketMatch } from './api-calls';

import { ByeCard, MatchupCard } from '@/features/playoff_bracket/bracket-cards';
import { type WildcardRoundItem } from '@/features/playoff_bracket/bracket-layout';
import { UI_COLORS } from '@/lib/color-constants';

export function BracketGrid({
  maxRound,
  wildcardRoundItems,
  semifinals,
  championship,
  recordMap,
  selectedMatchId,
  onSelectMatch,
}: {
  maxRound: number;
  wildcardRoundItems: WildcardRoundItem[];
  semifinals: BracketMatch[];
  championship: BracketMatch | undefined;
  recordMap: Record<string, string>;
  selectedMatchId: number | null;
  onSelectMatch: (id: number | null) => void;
}) {
  return (
    <div className="overflow-x-auto -mx-6 px-6 mb-6">
      <div
        className={`grid ${maxRound >= 3 ? 'grid-cols-[1fr_8px_1fr_8px_1fr]' : 'grid-cols-[1fr_8px_1fr]'} gap-0 items-stretch ${maxRound >= 3 ? 'min-w-[560px]' : 'min-w-[380px]'}`}
      >
        {/* Wild Card Round (6-team+ formats only) */}
        {maxRound >= 3 && (
          <div className="flex flex-col">
            <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
              Wild card
            </div>
            <div className="flex-1 flex flex-col justify-around">
              {wildcardRoundItems.map((item, idx) => (
                <div key={idx} className="flex flex-col gap-2.5">
                  {item.byeTeam && <ByeCard team={item.byeTeam} />}
                  {item.wildcardMatch && (
                    <MatchupCard
                      match={item.wildcardMatch}
                      played={true}
                      onClick={() =>
                        onSelectMatch(
                          item.wildcardMatch?.match_id === selectedMatchId
                            ? null
                            : (item.wildcardMatch?.match_id ?? null),
                        )
                      }
                      record1={recordMap[item.wildcardMatch.team_1_id] ?? null}
                      record2={recordMap[item.wildcardMatch.team_2_id] ?? null}
                    />
                  )}
                  {idx === 0 && <div className="h-8" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connector 1 (6-team+ formats only) */}
        {maxRound >= 3 && (
          <div className="flex flex-col justify-around pt-11">
            <svg
              width="20"
              height="58"
              viewBox="0 0 20 58"
              overflow="visible"
              className="block"
            >
              <path
                d="M0,15 H10 V43 H0"
                stroke="hsl(var(--border))"
                strokeWidth="1"
                fill="none"
              />
              <line
                x1="10"
                y1="29"
                x2="20"
                y2="29"
                stroke="hsl(var(--border))"
                strokeWidth="1"
              />
            </svg>
            <svg
              width="20"
              height="58"
              viewBox="0 0 20 58"
              overflow="visible"
              className="block"
            >
              <path
                d="M0,15 H10 V43 H0"
                stroke="hsl(var(--border))"
                strokeWidth="1"
                fill="none"
              />
              <line
                x1="10"
                y1="29"
                x2="20"
                y2="29"
                stroke="hsl(var(--border))"
                strokeWidth="1"
              />
            </svg>
          </div>
        )}

        {/* Semifinals */}
        <div className="flex flex-col">
          <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
            Semifinals
          </div>
          <div className="flex-1 flex flex-col justify-around">
            {semifinals.map((match) => (
              <MatchupCard
                key={match.match_id}
                match={match}
                played={true}
                onClick={() =>
                  onSelectMatch(
                    match.match_id === selectedMatchId ? null : match.match_id,
                  )
                }
                record1={recordMap[match.team_1_id] ?? null}
                record2={recordMap[match.team_2_id] ?? null}
              />
            ))}
          </div>
        </div>

        {/* Connector 2 */}
        <div className="flex flex-col justify-around pt-11">
          <svg
            width="20"
            height="130"
            viewBox="0 0 20 130"
            overflow="visible"
            className="block"
          >
            <path
              d="M0,25 H10 V105 H0"
              stroke="hsl(var(--border))"
              strokeWidth="1"
              fill="none"
            />
            <line
              x1="10"
              y1="65"
              x2="20"
              y2="65"
              stroke="hsl(var(--border))"
              strokeWidth="1"
            />
          </svg>
        </div>

        {/* Championship */}
        <div className="flex flex-col">
          <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
            Championship
          </div>
          <div className="flex-1 flex flex-col justify-around">
            {championship && (
              <MatchupCard
                match={championship}
                extraClass={`border-2`}
                extraStyle={{ borderColor: UI_COLORS.gold }}
                played={true}
                onClick={() =>
                  onSelectMatch(
                    championship.match_id === selectedMatchId
                      ? null
                      : championship.match_id,
                  )
                }
                record1={recordMap[championship.team_1_id] ?? null}
                record2={recordMap[championship.team_2_id] ?? null}
                championId={championship.winner}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
