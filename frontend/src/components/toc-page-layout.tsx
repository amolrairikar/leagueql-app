import { ArrowLeft } from 'lucide-react';
import { type ReactNode, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';

/** A single entry in the sticky table-of-contents sidebar. */
export interface TocItem {
  /** The `id` of the target `<section>` this entry scrolls to. */
  id: string;
  /** The label shown in the sidebar. */
  label: string;
}

interface TocPageLayoutProps {
  title: string;
  subtitle: ReactNode;
  /** Heading above the sidebar list, e.g. "Table of Contents" or "Releases". */
  tocLabel: string;
  tocItems: TocItem[];
  /** The `<section id=...>` blocks that make up the page body. */
  children: ReactNode;
}

/**
 * Shared shell for long, anchor-navigated content pages (privacy policy,
 * changelog, extension privacy): a back button, scroll-to-top on mount, a sticky
 * table-of-contents sidebar that smooth-scrolls to each section, and the page
 * header. Each page supplies only its title, subtitle, TOC entries, and body.
 */
export default function TocPageLayout({
  title,
  subtitle,
  tocLabel,
  tocItems,
  children,
}: TocPageLayoutProps) {
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="container mx-auto max-w-6xl pt-16 pb-8 px-4">
      <Button
        variant="ghost"
        onClick={() => void navigate(-1)}
        className="mb-6 cursor-pointer"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <div className="flex gap-10">
        <aside className="hidden md:block w-52 shrink-0">
          <div className="sticky top-8 space-y-1">
            <p className="text-sm font-semibold mb-3">{tocLabel}</p>
            {tocItems.map((item) => (
              <button
                key={item.id}
                onClick={() => scrollToSection(item.id)}
                className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-1 cursor-pointer"
              >
                {item.label}
              </button>
            ))}
          </div>
        </aside>

        <div className="flex-1 space-y-8">
          <div>
            <h1 className="text-4xl font-bold">{title}</h1>
            <p className="text-sm text-muted-foreground mt-2">{subtitle}</p>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
