import { cn } from '@/lib/utils';

export function BracketLoading() {
  return (
    <div className="text-center py-12">
      <p className="text-muted-foreground">Loading playoff bracket...</p>
    </div>
  );
}

/** Demo-only segmented control switching between the bracket and the predictor. */
export function DemoBracketToggle({
  value,
  onChange,
}: {
  value: 'bracket' | 'predictor';
  onChange: (v: 'bracket' | 'predictor') => void;
}) {
  const options: { key: 'bracket' | 'predictor'; label: string }[] = [
    { key: 'bracket', label: 'Bracket' },
    { key: 'predictor', label: 'Playoff Race' },
  ];
  return (
    <div className="inline-flex items-center gap-1 p-1 mb-6 rounded-lg border border-border bg-card">
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          onClick={() => onChange(o.key)}
          aria-pressed={value === o.key}
          className={cn(
            'text-[13px] font-medium px-3 py-1.5 rounded-md',
            value === o.key
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
