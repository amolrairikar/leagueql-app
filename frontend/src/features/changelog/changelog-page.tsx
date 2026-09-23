import TocPageLayout, { type TocItem } from '@/components/toc-page-layout';
import { CHANGELOG } from '@/features/changelog/constants';

/** Anchor id for a release, e.g. "v1-1-0". */
function releaseId(version: string): string {
  return `v${version.replace(/\./g, '-')}`;
}

const tocItems: TocItem[] = CHANGELOG.map((release) => ({
  id: releaseId(release.version),
  label: `v${release.version}`,
}));

export default function ChangelogPage() {
  return (
    <TocPageLayout
      title="Changelog"
      subtitle="All notable changes to LeagueQL are documented here."
      tocLabel="Releases"
      tocItems={tocItems}
    >
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
              <h3 className="font-semibold text-foreground">{section.title}</h3>
              <ul className="list-disc pl-6 space-y-1 text-muted-foreground leading-relaxed">
                {section.items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
    </TocPageLayout>
  );
}
