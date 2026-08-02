/**
 * Label for the Season Champion award when no champion is recorded. The most recent season
 * can still be mid-playoffs → "TBD" / "Season in progress"; any earlier season is complete, so
 * a missing champion there is a finished season with no recorded title → "N/A" / "No champion".
 */
export function noChampionAward(isLatestSeason: boolean): {
  title: string;
  subtitle: string;
} {
  return isLatestSeason
    ? { title: 'TBD', subtitle: 'Season in progress' }
    : { title: 'N/A', subtitle: 'No champion' };
}
