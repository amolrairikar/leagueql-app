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
import { ApiError } from '@/lib/api-client';
import { getLeagueCookies, type Platform } from '@/lib/cookie-handler';
import { downloadLeagueZip } from '@/lib/download';
import { ErrorAlert } from '@/lib/error-alert';

// A multi-season export response can exceed Lambda's 6 MB response limit, so each
// season is requested on its own and the results are merged into a single ZIP.
const EXPORT_CONCURRENCY = 3;

type ExportBundle = Record<string, Record<string, unknown[]>>;

/**
 * Fetch each season in its own request (at most `EXPORT_CONCURRENCY` in flight) and
 * merge the results. A 404 means the season has no data and is omitted; any other
 * failure aborts the export (no further seasons are started).
 */
async function fetchSeasonBundles(
  leagueId: string,
  platform: Platform,
  seasons: string[],
): Promise<ExportBundle> {
  const bundle: ExportBundle = {};
  const queue = [...seasons];
  const state: { failure: Error | null } = { failure: null };

  async function worker() {
    while (state.failure === null) {
      const season = queue.shift();
      if (season === undefined) return;
      try {
        const res = await exportLeague(leagueId, platform, [season]);
        Object.assign(bundle, res.data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) continue;
        state.failure = err instanceof Error ? err : new Error(String(err));
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(EXPORT_CONCURRENCY, seasons.length) }, () =>
      worker(),
    ),
  );
  if (state.failure !== null) throw state.failure;
  return bundle;
}

/**
 * Export a league's processed data (frontend/export-league-data). The member picks
 * which onboarded seasons to include; on confirm each selected season's processed
 * views are fetched in its own request (backend/league-export) and downloaded as a
 * single ZIP of one JSON file per view per season.
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
      const exportedAt = new Date().toISOString();
      const bundle = await fetchSeasonBundles(leagueId, platform, selected);
      if (Object.keys(bundle).length === 0) {
        throw new Error('No data found for the selected seasons.');
      }
      await downloadLeagueZip(`leagueql_export_${leagueId}.zip`, bundle, {
        leagueId,
        platform,
        exportedAt,
      });
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
        <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
          <p>
            Tip: upload the ZIP to an AI assistant like Claude or ChatGPT to ask
            questions about your league. Try:
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>
              &ldquo;Write a season-in-review recap for this league.&rdquo;
            </li>
            <li>&ldquo;Roast my draft — who were my biggest busts?&rdquo;</li>
            <li>
              &ldquo;Build a profile for each manager, highlighting their
              tendencies.&rdquo;
            </li>
          </ul>
        </div>
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
                Export all seasons
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
