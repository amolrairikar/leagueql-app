import JSZip from 'jszip';

import {
  buildExportManifest,
  buildExportReadme,
  type ExportBundle,
  type ExportMeta,
} from '@/lib/export-guide';

export type { ExportBundle } from '@/lib/export-guide';

/**
 * Build a ZIP of one JSON file per view per season from an export bundle and
 * trigger a browser download. Each entry is named `<season>_<view>.json`; a
 * `README.md` data guide and a `manifest.json` sit at the ZIP root so the export
 * can be handed to an AI assistant as-is.
 *
 * This is the browser-download step for the league-data export
 * (frontend/export-league-data): the backend returns the bundle as JSON and the
 * ZIP is assembled client-side so the API stays a plain JSON read.
 */
export async function downloadLeagueZip(
  filename: string,
  bundle: ExportBundle,
  meta: ExportMeta,
): Promise<void> {
  const zip = new JSZip();
  zip.file('README.md', buildExportReadme(bundle, meta));
  zip.file(
    'manifest.json',
    JSON.stringify(buildExportManifest(bundle, meta), null, 2),
  );
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
