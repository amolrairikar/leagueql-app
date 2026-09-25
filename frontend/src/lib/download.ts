import JSZip from 'jszip';

/** An export bundle: season → view name → rows (matches the /export response `data`). */
export type ExportBundle = Record<string, Record<string, unknown[]>>;

/**
 * Build a ZIP of one JSON file per view per season from an export bundle and
 * trigger a browser download. Each entry is named `<season>_<view>.json`.
 *
 * This is the browser-download step for the league-data export
 * (frontend/export-league-data): the backend returns the bundle as JSON and the
 * ZIP is assembled client-side so the API stays a plain JSON read.
 */
export async function downloadLeagueZip(
  filename: string,
  bundle: ExportBundle,
): Promise<void> {
  const zip = new JSZip();
  for (const [season, views] of Object.entries(bundle)) {
    for (const [view, rows] of Object.entries(views)) {
      zip.file(`${season}_${view}.json`, JSON.stringify(rows, null, 2));
    }
  }
  const blob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
