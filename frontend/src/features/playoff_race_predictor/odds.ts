/** Format a 0..1 playoff-odds value: exact 0/100, `<1%`/`>99%` extremes, else integer %. */
export function formatOdds(odds: number | null): string {
  if (odds === null) return '—';
  if (odds <= 0) return '0%';
  if (odds >= 1) return '100%';
  if (odds < 0.01) return '<1%';
  if (odds > 0.99) return '>99%';
  return `${Math.round(odds * 100)}%`;
}
