import { Info, TriangleAlert } from 'lucide-react';

export function SectionLink({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={() =>
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
      }
      className="text-primary underline underline-offset-2 hover:text-primary/80 cursor-pointer align-baseline"
    >
      {children}
    </button>
  );
}

export function Callout({
  children,
  variant = 'default',
}: {
  children: React.ReactNode;
  variant?: 'default' | 'warning';
}) {
  const styles =
    variant === 'warning'
      ? 'bg-amber-50/80 border-amber-300 text-amber-800 dark:bg-amber-950/30 dark:border-amber-700 dark:text-amber-300'
      : 'bg-muted/50 border-border text-muted-foreground';
  const Icon = variant === 'warning' ? TriangleAlert : Info;
  return (
    <div className={`rounded-md border px-4 py-3 text-sm ${styles}`}>
      <span className="flex items-start gap-2">
        <Icon className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{children}</span>
      </span>
    </div>
  );
}

export function SectionHeading({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <h2
      id={id}
      data-section
      className="text-2xl font-semibold mb-4 scroll-mt-24"
    >
      {children}
    </h2>
  );
}

export function SubHeading({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <h3
      id={id}
      data-section
      className="text-lg font-semibold mb-2 scroll-mt-24"
    >
      {children}
    </h3>
  );
}

export function SubSubHeading({
  id,
  children,
}: {
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <h4
      id={id}
      data-section={id ? true : undefined}
      className="text-base font-medium mb-3 scroll-mt-24"
    >
      {children}
    </h4>
  );
}

// A heading one level below SubSubHeading. Intentionally has no id /
// `data-section`, so it never appears in the table of contents nor drives the
// scroll-spy active state — used for in-section labels like the Sleeper
// midseason vs. new-season refresh split.
export function MinorHeading({ children }: { children: React.ReactNode }) {
  return (
    <h5 className="text-sm font-semibold text-foreground mb-1.5">{children}</h5>
  );
}

export function DocTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | React.ReactNode)[][];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b">
            {headers.map((h) => (
              <th
                key={h}
                className="text-left py-2 pr-6 font-semibold text-foreground whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="text-muted-foreground">
          {rows.map((row, i) => (
            <tr
              key={i}
              className={i < rows.length - 1 ? 'border-b border-border/50' : ''}
            >
              {row.map((cell, j) => (
                <td
                  key={j}
                  className={`py-2 pr-6 leading-relaxed ${j === 0 ? 'font-medium whitespace-nowrap' : ''}`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
