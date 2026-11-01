import { useEffect } from 'react';

import { ConnectingALeagueSection } from '@/features/instructions/section-connecting-a-league';
import { GettingStartedSection } from '@/features/instructions/section-getting-started';
import { ManagingYourLeagueSection } from '@/features/instructions/section-managing-your-league';
import { NavigationSection } from '@/features/instructions/section-navigation';
import { TocSidebar } from '@/features/instructions/toc-sidebar';
import { useScrollSpy } from '@/features/instructions/use-scroll-spy';

export default function InstructionsPage() {
  const { activeId, contentRef } = useScrollSpy('getting-started');

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="container mx-auto flex h-full max-w-6xl flex-col px-4 pt-20">
      <div className="mb-10">
        <h1 className="text-4xl font-bold">User Guide</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Everything you need to know about using LeagueQL.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 gap-12">
        <TocSidebar activeId={activeId} />

        <div
          ref={contentRef}
          className="min-w-0 flex-1 space-y-12 overflow-y-auto overscroll-contain pb-8 pr-2"
        >
          <GettingStartedSection />
          <ConnectingALeagueSection />
          <NavigationSection />
          <ManagingYourLeagueSection />
        </div>
      </div>
    </div>
  );
}
