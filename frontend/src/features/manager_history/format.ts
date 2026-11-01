export function managerInitials(username: string): string {
  const parts = username
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length >= 2)
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

export function ordinal(n: number) {
  const s = ['th', 'st', 'nd', 'rd'],
    v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

// ── Data processing ───────────────────────────────────────────────────────────
