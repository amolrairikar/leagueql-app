import { TOC_ITEMS } from '@/features/instructions/toc';

export function TocSidebar({ activeId }: { activeId: string }) {
  return (
    <aside className="hidden w-52 shrink-0 lg:flex lg:min-h-0 lg:flex-col">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
        On this page
      </p>
      <nav className="min-h-0 flex-1 cursor-pointer space-y-0.5 overflow-y-auto overscroll-contain pr-2">
        {TOC_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() =>
              document
                .getElementById(item.id)
                ?.scrollIntoView({ behavior: 'smooth' })
            }
            className={[
              'block w-full text-left text-sm py-1 transition-colors rounded cursor-pointer',
              item.level === 2 ? 'pl-3' : item.level === 3 ? 'pl-5' : '',
              activeId === item.id
                ? 'text-primary font-medium'
                : 'text-muted-foreground hover:text-foreground',
            ].join(' ')}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
