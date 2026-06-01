import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Derives a 1–2 character avatar initial from a display name / username.
 * Uses the first letters of the first two alphanumeric words, falling back to
 * the first two characters for single-word names.
 */
export function initials(name: string): string {
  const parts = name
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length >= 2)
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

/**
 * Returns `a` as a whole-number percentage of the `a + b` total (rounded).
 * Defaults to 50 when both are zero (an even split with no data).
 */
export function pct(a: number, b: number): number {
  const total = a + b;
  return total === 0 ? 50 : Math.round((a / total) * 100);
}
