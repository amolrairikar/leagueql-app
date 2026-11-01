import { SectionHeading } from '@/features/instructions/doc-components';

export function NavigationSection() {
  return (
    <section>
      <SectionHeading id="navigation">Navigation</SectionHeading>
      <p className="text-muted-foreground leading-relaxed mb-4">
        All pages are accessible from the sidebar on the left side of the
        screen. The sidebar can be collapsed to icon-only mode using the toggle
        button in the top header.
      </p>
      <p className="text-muted-foreground leading-relaxed mb-2">
        The top header also contains:
      </p>
      <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-4">
        <li>
          <strong className="text-foreground">LeagueQL logo</strong>: returns
          you to the landing page
        </li>
        <li>
          <strong className="text-foreground">Changelog, Docs</strong>: links to
          the changelog and user docs
        </li>
        <li>
          <strong className="text-foreground">Dark/light mode toggle</strong>:
          toggle between dark mode and light mode, defaults to your system
          preferences
        </li>
      </ul>
    </section>
  );
}
