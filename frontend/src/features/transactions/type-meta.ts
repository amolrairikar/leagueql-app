import { Gavel, type LucideIcon, Repeat, UserPlus } from 'lucide-react';

/**
 * Per-type presentation: label, icon, and the accent classes for the type chip. The commissioner
 * entry is a neutral fallback — it is never filterable, but a stray commissioner move still renders
 * a sensible chip.
 */
export const TYPE_META: Record<
  string,
  { label: string; Icon: LucideIcon; chip: string }
> = {
  trade: {
    label: 'Trade',
    Icon: Repeat,
    chip: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
  },
  waiver: {
    label: 'Waiver',
    Icon: Gavel,
    chip: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  free_agent: {
    label: 'Free Agent',
    Icon: UserPlus,
    chip: 'bg-sky-500/10 text-sky-600 dark:text-sky-400',
  },
  commissioner: {
    label: 'Commissioner',
    Icon: Repeat,
    chip: 'bg-muted text-muted-foreground',
  },
};

export function typeMeta(type: string) {
  return TYPE_META[type] ?? TYPE_META.commissioner;
}
