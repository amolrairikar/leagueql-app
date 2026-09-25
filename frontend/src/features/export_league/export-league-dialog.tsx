import { useState } from 'react';

import { exportLeague } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { downloadLeagueZip } from '@/lib/download';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Export a league's processed data (frontend/export-league-data). The member picks
 * which onboarded seasons to include; on confirm the selected seasons' processed
 * views are fetched (backend/league-export) and downloaded as a ZIP of one JSON
 * file per view per season.
 */
export function ExportLeagueDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { leagueId, platform, seasons } = getLeagueCookies();
  // Newest season first, matching the season selectors elsewhere in the app.
  const sortedSeasons = [...seasons].sort().reverse();
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allSelected =
    sortedSeasons.length > 0 && selected.length === sortedSeasons.length;

  function reset() {
    setSelected([]);
    setError(null);
    setLoading(false);
  }

  function toggleSeason(season: string) {
    setSelected((prev) =>
      prev.includes(season)
        ? prev.filter((s) => s !== season)
        : [...prev, season],
    );
  }

  function toggleSelectAll() {
    setSelected(allSelected ? [] : [...sortedSeasons]);
  }

  async function handleExport() {
    setLoading(true);
    setError(null);
    try {
      const res = await exportLeague(leagueId, platform, selected);
      await downloadLeagueZip(`leagueql_export_${leagueId}.zip`, res.data);
      onOpenChange(false);
      reset();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to export league data.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) reset();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export league data</DialogTitle>
          <DialogDescription>
            Choose the seasons to export. You&apos;ll get a ZIP file with one
            JSON file per data view for each season you pick.
          </DialogDescription>
        </DialogHeader>
        {sortedSeasons.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This league has no seasons available to export.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 border-b pb-2">
              <input
                id="export-select-all"
                type="checkbox"
                className="size-4 cursor-pointer accent-primary"
                checked={allSelected}
                onChange={toggleSelectAll}
              />
              <Label htmlFor="export-select-all" className="cursor-pointer">
                Select all
              </Label>
            </div>
            {sortedSeasons.map((season) => (
              <div key={season} className="flex items-center gap-2">
                <input
                  id={`export-season-${season}`}
                  type="checkbox"
                  className="size-4 cursor-pointer accent-primary"
                  checked={selected.includes(season)}
                  onChange={() => toggleSeason(season)}
                />
                <Label
                  htmlFor={`export-season-${season}`}
                  className="cursor-pointer"
                >
                  {season}
                </Label>
              </div>
            ))}
          </div>
        )}
        {error && <ErrorAlert message={error} />}
        <DialogFooter>
          <Button
            className="cursor-pointer"
            disabled={loading || selected.length === 0}
            onClick={() => void handleExport()}
          >
            {loading && <Spinner className="size-4" />}
            Export
          </Button>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
