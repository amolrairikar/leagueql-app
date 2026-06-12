import { ArrowLeft } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { CHANGELOG } from '@/features/changelog/constants';

/** Anchor id for a release, e.g. "v1-1-0". */
function releaseId(version: string): string {
  return `v${version.replace(/\./g, '-')}`;
}

export default function ChangelogPage() {
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
            <p className="text-sm font-semibold mb-3">Releases</p>
            {CHANGELOG.map((release) => (
              <button
                key={release.version}
                onClick={() => scrollToSection(releaseId(release.version))}
                className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-1 cursor-pointer"
              >
                v{release.version}
              </button>
            ))}
          </div>
        </aside>

        <div className="flex-1 space-y-8">
          <div>
            <h1 className="text-4xl font-bold">Changelog</h1>
            <p className="text-sm text-muted-foreground mt-2">
              All notable changes to LeagueQL are documented here.
            </p>
          </div>

          {CHANGELOG.map((release) => (
            <section
              key={release.version}
              id={releaseId(release.version)}
              className="space-y-4 scroll-mt-20"
            >
              <div className="flex items-baseline gap-3">
                <h2 className="text-2xl font-semibold">v{release.version}</h2>
                <span className="text-sm text-muted-foreground">
                  {release.date}
                </span>
              </div>

              {release.sections.map((section) => (
                <div key={section.title} className="space-y-2">
                  <h3 className="font-semibold text-foreground">
                    {section.title}
                  </h3>
                  <ul className="list-disc pl-6 space-y-1 text-muted-foreground leading-relaxed">
                    {section.items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
