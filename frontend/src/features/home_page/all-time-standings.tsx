import { Trophy } from 'lucide-react';
import { useMemo, useState } from 'react';

import { TeamAvatar } from '@/components/team-avatar';
import { Switch } from '@/components/ui/switch';
import {
  buildAllTimeStandings,
  type AllTimeStandingsData,
} from '@/features/home_page/all-time-data';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import { assignAvatarColors, avatarColor } from '@/lib/color-constants';

export function AllTimeStandingsTable({
  standings,
  matchups,
  migrationMapping,
}: AllTimeStandingsData) {
  const [showPlayoffs, setShowPlayoffs] = useState(false);

  // Owner-stable colors (alphabetical), matching the standings chart below
  const colorMap = useMemo(() => {
    const ownerMeta = new Map<string, ManagerStandingsItem>();
    for (const row of standings) {
      const id = migrationMapping.get(row.owner_id) ?? row.owner_id;
      const existing = ownerMeta.get(id);
      if (!existing || row.season.localeCompare(existing.season) > 0) {
        ownerMeta.set(id, row);
      }
    }
    const sorted = [...ownerMeta.entries()].sort((a, b) =>
      a[1].owner_username.localeCompare(b[1].owner_username),
    );
    return assignAvatarColors(sorted.map(([id]) => id));
  }, [standings, migrationMapping]);

  const rows = useMemo(
    () =>
      buildAllTimeStandings(
        standings,
        matchups,
        migrationMapping,
        showPlayoffs ? 'playoff' : 'regular',
      ),
    [standings, matchups, migrationMapping, showPlayoffs],
  );

  // Championships per owner (remapped through migration mapping)
  const championshipCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of standings) {
      if (row.champion === 'Yes') {
        const id = migrationMapping.get(row.owner_id) ?? row.owner_id;
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return counts;
  }, [standings, migrationMapping]);

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2.5">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          All-time standings
        </p>
        <div className="flex items-center gap-2.5">
          <span
            className={`text-[11px] font-medium ${
              showPlayoffs ? 'text-muted-foreground' : 'text-foreground'
            }`}
          >
            Regular season
          </span>
          <Switch
            checked={showPlayoffs}
            onCheckedChange={setShowPlayoffs}
            aria-label="Toggle between regular season and playoff standings"
            className="cursor-pointer"
          />
          <span
            className={`text-[11px] font-medium ${
              showPlayoffs ? 'text-foreground' : 'text-muted-foreground'
            }`}
          >
            Playoffs
          </span>
        </div>
      </div>

      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
        <div className="max-h-[70vh] overflow-auto">
          <table
            className="w-full border-collapse text-[13px]"
            style={{ tableLayout: 'fixed', minWidth: '480px' }}
          >
            <thead className="sticky top-0 z-20">
              <tr>
                <th
                  className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted sticky left-0 z-10"
                  style={{ width: '40%' }}
                >
                  Manager
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '9%' }}
                >
                  GP
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '17%' }}
                >
                  Record
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '12%' }}
                >
                  Win %
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '11%' }}
                >
                  PF/Game
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '11%' }}
                >
                  PA/Game
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3.5 py-8 text-center text-[13px] text-muted-foreground"
                  >
                    {showPlayoffs
                      ? 'No playoff games available.'
                      : 'No regular season games available.'}
                  </td>
                </tr>
              ) : (
                rows.map((row, i) => {
                  const winPct =
                    row.games > 0 ? (row.wins + 0.5 * row.ties) / row.games : 0;
                  return (
                    <tr
                      key={row.ownerId}
                      className="border-b border-border/50 last:border-0 bg-card"
                    >
                      <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
                        <div className="flex items-center gap-2">
                          <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                            {i + 1}
                          </span>
                          <TeamAvatar
                            teamLogo={row.teamLogo}
                            teamName={row.teamName}
                            ownerUsername={row.username}
                            color={colorMap.get(row.ownerId) ?? avatarColor(i)}
                          />
                          <span className="text-[13px] font-medium text-foreground truncate">
                            {row.username}
                          </span>
                          {(() => {
                            const titles =
                              championshipCounts.get(row.ownerId) ?? 0;
                            if (titles === 0) return null;
                            return (
                              <span
                                className="flex items-center shrink-0"
                                title={`${titles} championship${titles > 1 ? 's' : ''}`}
                                aria-label={`${titles} championship${titles > 1 ? 's' : ''}`}
                              >
                                {Array.from({ length: titles }).map((_, t) => (
                                  <Trophy
                                    key={t}
                                    className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500"
                                  />
                                ))}
                              </span>
                            );
                          })()}
                        </div>
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {row.games}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {`${row.wins}-${row.losses}-${row.ties}`}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {winPct.toFixed(3)}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {(row.pf / row.games).toFixed(1)}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {(row.pa / row.games).toFixed(1)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
