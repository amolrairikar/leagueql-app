import { ArrowLeft, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';

const TOC_ITEMS = [
  { id: 'getting-started', label: 'Getting Started', level: 1 },
  { id: 'demo-mode', label: 'Demo Mode', level: 2 },
  { id: 'authentication', label: 'Authentication', level: 2 },
  { id: 'connecting-a-league', label: 'Connecting a League', level: 2 },
  { id: 'espn-leagues', label: 'ESPN Leagues', level: 3 },
  { id: 'sleeper-leagues', label: 'Sleeper Leagues', level: 3 },
  { id: 'navigation', label: 'Navigation', level: 1 },
  { id: 'managing-your-league', label: 'Managing Your League', level: 1 },
  { id: 'refreshing-league-data', label: 'Refreshing League Data', level: 2 },
  { id: 'migrating-your-league', label: 'Migrating Your League', level: 2 },
  { id: 'switching-leagues', label: 'Switching Leagues', level: 2 },
  { id: 'deleting-a-league', label: 'Deleting a League', level: 2 },
  { id: 'faq-and-troubleshooting', label: 'FAQ & Troubleshooting', level: 1 },
] as const;

interface FaqItem {
  q: string;
  a?: React.ReactNode;
  steps?: string[];
  note?: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    q: 'Why do I need to provide my ESPN cookies?',
    a: 'ESPN private leagues require authentication. The SWID and ESPN S2 cookies prove you are a member of the league. They are used once to fetch data and are not stored.',
  },
  {
    q: 'Where do I find my ESPN cookies?',
    steps: [
      'Open your browser and go to fantasy.espn.com',
      'Log in to your account',
      'Open DevTools (F12 or Cmd+Option+I)',
      'Go to Application → Cookies → fantasy.espn.com',
      'Find SWID and espn_s2 and copy their values',
    ],
    note: 'With the LeagueQL ESPN Cookie Helper Chrome extension installed, you can skip these steps — just log into ESPN, then click "Autofill from ESPN" on the onboarding form.',
  },
  {
    q: 'The connection timed out — what happened?',
    a: 'If the page shows a timeout error, note the operation ID displayed and try again. If the issue persists, file a bug report with the operation ID so it can be investigated.',
  },
  {
    q: 'My data looks outdated — how do I refresh it?',
    a: (
      <>
        For ESPN leagues, click <InlineCode>Refresh League</InlineCode> in the
        sidebar and re-submit your league credentials. Sleeper leagues will
        refresh automatically each week during the season.
      </>
    ),
  },
  {
    q: 'Why is there a subscription for the app?',
    a: 'The subscription helps cover the cost of hosting the app and the time spent developing and maintaining it.',
  },
  {
    q: 'Can I connect more than one league?',
    a: (
      <>
        Yes. Use the <InlineCode>View Another League</InlineCode> option in the
        sidebar to view or onboard another league. Each league is stored
        independently.
      </>
    ),
  },
];

function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">
      {children}
    </code>
  );
}

function Callout({
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
  return (
    <div className={`rounded-md border px-4 py-3 text-sm ${styles}`}>
      {variant === 'warning' ? (
        <span className="flex items-start gap-2">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{children}</span>
        </span>
      ) : (
        children
      )}
    </div>
  );
}

function SectionHeading({
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

function SubHeading({
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

function SubSubHeading({
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

function DocTable({
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

export default function InstructionsPage() {
  const navigate = useNavigate();
  const [activeId, setActiveId] = useState('getting-started');

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    const headings = document.querySelectorAll('[data-section]');
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: '-10% 0% -80% 0%' },
    );
    headings.forEach((h) => observer.observe(h));
    return () => observer.disconnect();
  }, []);

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

      <div className="mb-10">
        <h1 className="text-4xl font-bold">User Guide</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Everything you need to know about using LeagueQL.
        </p>
      </div>

      <div className="flex gap-12">
        <aside className="hidden lg:block w-52 shrink-0">
          <div className="sticky top-24 max-h-[calc(100svh-8rem)] overflow-y-auto">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
              On this page
            </p>
            <nav className="space-y-0.5">
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
          </div>
        </aside>

        <div className="flex-1 min-w-0 space-y-12">
          {/* Getting Started */}
          <section>
            <SectionHeading id="getting-started">
              Getting Started
            </SectionHeading>
            <p className="text-muted-foreground leading-relaxed mb-6">
              This app is designed for a web browser, not a mobile browser.
              While efforts have been made to make the mobile experience closely
              reflect the web experience, your experience may vary on mobile
              devices.
            </p>

            <div className="space-y-6">
              <div>
                <SubHeading id="demo-mode">Demo Mode</SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Want to explore the app before connecting your own league?
                  Click <InlineCode>View Demo</InlineCode> on the landing page.
                  A sample league is pre-loaded so you can navigate every page.
                  Click
                  <InlineCode>Exit Demo</InlineCode> in the sidebar to return to
                  the landing page and connect your own league.
                </p>
              </div>

              <div>
                <SubHeading id="authentication">Authentication</SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  LeagueQL uses Clerk for authentication. From the landing page,
                  click <InlineCode>Connect Your League</InlineCode> and sign in
                  when prompted. After signing in you are returned to the
                  landing page.
                </p>
              </div>

              <div>
                <SubHeading id="connecting-a-league">
                  Connecting a League
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Click <InlineCode>Connect Your League</InlineCode> on the
                  landing page. A small form will appear. Select your platform
                  (ESPN or Sleeper) and enter your league ID, then click{' '}
                  <InlineCode>Connect</InlineCode>.
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-6">
                  <li>
                    <strong className="text-foreground">
                      Sleeper leagues:
                    </strong>{' '}
                    The app fetches or onboards your league automatically (no
                    credentials required as the underlying Sleeper API is
                    read-only). Onboarding typically takes ~45 seconds. On
                    success you are redirected to your league&apos;s home
                    dashboard.
                  </li>
                  <li>
                    <strong className="text-foreground">ESPN leagues:</strong>{' '}
                    If your league has already been onboarded, you are taken
                    straight to your dashboard. If it is a new league, you are
                    taken to a form to enter your ESPN credentials.
                  </li>
                </ul>

                <SubSubHeading id="espn-leagues">ESPN Leagues</SubSubHeading>
                <div className="mb-4">
                  <DocTable
                    headers={['Field', 'Description']}
                    rows={[
                      [
                        'League ID',
                        <>
                          The numeric ID in your ESPN fantasy URL (e.g.{' '}
                          <InlineCode>?leagueId=12345</InlineCode>)
                        </>,
                      ],
                      [
                        'Latest Season',
                        'The most recent year your league was active',
                      ],
                      [
                        'SWID Cookie',
                        <>
                          Found in your browser&apos;s DevTools under{' '}
                          <strong className="text-foreground">
                            Application → Cookies → fantasy.espn.com
                          </strong>
                        </>,
                      ],
                      ['ESPN S2 Cookie', 'Found in the same location as SWID'],
                    ]}
                  />
                </div>
                <Callout variant="warning">
                  Your SWID and ESPN S2 cookies are only transmitted once over
                  HTTPS to fetch your data and are never stored by LeagueQL.
                </Callout>
              </div>

              <div>
                <SubSubHeading id="sleeper-leagues">
                  Sleeper Leagues
                </SubSubHeading>
                <div className="mb-4">
                  <DocTable
                    headers={['Field', 'Description']}
                    rows={[
                      [
                        'League ID',
                        <>
                          The numeric ID in your Sleeper league URL (e.g.{' '}
                          <InlineCode>
                            https://sleeper.com/leagues/12345
                          </InlineCode>
                          )
                        </>,
                      ],
                    ]}
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Navigation */}
          <section>
            <SectionHeading id="navigation">Navigation</SectionHeading>
            <p className="text-muted-foreground leading-relaxed mb-4">
              All pages are accessible from the sidebar on the left side of the
              screen. The sidebar can be collapsed to icon-only mode using the
              toggle button in the top header.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-2">
              The top header also contains:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-4">
              <li>
                <strong className="text-foreground">LeagueQL logo</strong> —
                returns you to the landing page
              </li>
              <li>
                <strong className="text-foreground">Changelog, Docs</strong> —
                links to the changelog and user docs
              </li>
              <li>
                <strong className="text-foreground">
                  Dark/light mode toggle
                </strong>{' '}
                — toggle between dark mode and light mode, defaults to your
                system preferences
              </li>
            </ul>
            <p className="text-muted-foreground leading-relaxed">
              At the bottom of the sidebar you will find league management
              options: refresh your league, migrate to another platform, switch
              to view another league, submit a feature request, and delete the
              current league.
            </p>
          </section>

          {/* Managing Your League */}
          <section>
            <SectionHeading id="managing-your-league">
              Managing Your League
            </SectionHeading>
            <div className="space-y-8">
              <div>
                <SubHeading id="refreshing-league-data">
                  Refreshing League Data
                </SubHeading>
                <SubSubHeading>ESPN</SubSubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Click the Refresh League button in the sidebar. This navigates
                  you to the league connection page where you can submit your
                  credentials again. The system detects the league already
                  exists and runs a refresh instead of a full re-onboard, which
                  is faster.
                </p>
                <SubSubHeading>Sleeper</SubSubHeading>
                <p className="text-muted-foreground leading-relaxed mb-2">
                  You do not need to refresh your Sleeper league during the
                  active season. An automated process runs weekly every Tuesday
                  morning to update your league data.
                </p>
                <p className="text-muted-foreground leading-relaxed">
                  If refreshing for a new season, enter your new league ID using
                  the <InlineCode>Connect Your League</InlineCode> form
                  (accessible via <InlineCode>View Another League</InlineCode>{' '}
                  in the sidebar). Sleeper league IDs change each season. The
                  system automatically associates the new league ID with your
                  existing history.
                </p>
              </div>

              <div>
                <SubHeading id="migrating-your-league">
                  Migrating Your League
                </SubHeading>
                <Callout variant="warning">
                  <strong className="text-foreground">
                    Experimental feature
                  </strong>{' '}
                  — League migration cannot be undone. All-time metrics will be
                  recalculated to reflect the merged history across both
                  platforms.
                </Callout>
                <p className="text-muted-foreground leading-relaxed mt-4 mb-4">
                  Use this when your league moves from one platform to another
                  in the offseason (ESPN → Sleeper or Sleeper → ESPN). Click
                  Migrate League in the sidebar settings.
                </p>
                <p className="text-muted-foreground mb-3">
                  The wizard walks you through four steps:
                </p>
                <ol className="list-decimal pl-6 space-y-2 text-muted-foreground leading-relaxed">
                  <li>
                    <strong className="text-foreground">
                      Confirm current league:
                    </strong>{' '}
                    Review your existing league name, platform, and season
                    history.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Enter new league details:
                    </strong>{' '}
                    Provide the league ID on the new platform. For ESPN, you
                    will also need to enter the latest season, SWID, and ESPN S2
                    cookies.
                  </li>
                  <li>
                    <strong className="text-foreground">Map managers:</strong>{' '}
                    Match each manager to their account on the new platform.
                    Managers who left can be marked as &quot;Not returning&quot;
                    and their historical stats remain visible.
                  </li>
                  <li>
                    <strong className="text-foreground">
                      Preview & confirm:
                    </strong>{' '}
                    Review the migration summary and confirm. The migration runs
                    in the background (typically ~1 minute).
                  </li>
                </ol>
              </div>

              <div>
                <SubHeading id="switching-leagues">
                  Switching Leagues
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Click <InlineCode>View Another League</InlineCode> in the
                  sidebar. You are taken back to the landing page where you can
                  enter a different league ID using the inline connect form.
                </p>
              </div>

              <div>
                <SubHeading id="deleting-a-league">
                  Deleting a League
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Click <InlineCode>Delete League</InlineCode> at the bottom of
                  the sidebar. This permanently removes all stored data for the
                  league from LeagueQL&apos;s backend. This action cannot be
                  undone.
                </p>
              </div>
            </div>
          </section>

          {/* FAQ */}
          <section>
            <SectionHeading id="faq-and-troubleshooting">
              FAQ and Troubleshooting
            </SectionHeading>
            <div className="space-y-6">
              {FAQ_ITEMS.map((item) => (
                <div key={item.q}>
                  <p className="font-semibold text-foreground mb-2">{item.q}</p>
                  {'a' in item && item.a && (
                    <p className="text-muted-foreground leading-relaxed">
                      {item.a}
                    </p>
                  )}
                  {'steps' in item && item.steps && (
                    <ol className="list-decimal pl-6 space-y-1 text-muted-foreground leading-relaxed">
                      {item.steps.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ol>
                  )}
                  {'note' in item && item.note && (
                    <p className="text-sm text-muted-foreground mt-2 italic">
                      {item.note}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
