import { Info, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import espnOnboardFormScreenshot from '@/assets/espn-onboard-form-screenshot.png';
import espnVerifyMembershipScreenshot from '@/assets/espn-verify-membership-screenshot.png';
import { Kbd } from '@/components/ui/kbd';
import { ESPN_EXTENSION_URL } from '@/lib/espn-extension';

const TOC_ITEMS = [
  { id: 'getting-started', label: 'Getting Started', level: 1 },
  { id: 'demo-mode', label: 'Demo Mode', level: 2 },
  { id: 'authentication', label: 'Authentication', level: 2 },
  { id: 'connecting-a-league', label: 'Connecting a League', level: 1 },
  { id: 'espn-leagues', label: 'ESPN', level: 2 },
  { id: 'espn-form-fields', label: 'Form Fields', level: 3 },
  { id: 'chrome-extension', label: 'Chrome Extension', level: 3 },
  { id: 'sleeper-leagues', label: 'Sleeper', level: 2 },
  { id: 'sleeper-form-fields', label: 'Form Fields', level: 3 },
  { id: 'league-ownership', label: 'League Ownership', level: 2 },
  { id: 'joining-an-espn-league', label: 'Joining an ESPN League', level: 3 },
  { id: 'transferring-ownership', label: 'Transferring Ownership', level: 3 },
  { id: 'navigation', label: 'Navigation', level: 1 },
  { id: 'managing-your-league', label: 'Managing Your League', level: 1 },
  { id: 'refreshing-league-data', label: 'Refreshing League Data', level: 2 },
  { id: 'refresh-espn', label: 'ESPN', level: 3 },
  { id: 'refresh-sleeper', label: 'Sleeper', level: 3 },
  { id: 'migrating-your-league', label: 'Migrating Your League', level: 2 },
  { id: 'switching-leagues', label: 'Switching Leagues', level: 2 },
  { id: 'deleting-a-league', label: 'Deleting a League', level: 2 },
] as const;

function SectionLink({
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

// A heading one level below SubSubHeading. Intentionally has no id /
// `data-section`, so it never appears in the table of contents nor drives the
// scroll-spy active state — used for in-section labels like the Sleeper
// midseason vs. new-season refresh split.
function MinorHeading({ children }: { children: React.ReactNode }) {
  return (
    <h5 className="text-sm font-semibold text-foreground mb-1.5">{children}</h5>
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
  const [activeId, setActiveId] = useState('getting-started');
  const tocItems = TOC_ITEMS;

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
    <div className="container mx-auto flex h-full max-w-6xl flex-col px-4 pt-20">
      <div className="mb-10">
        <h1 className="text-4xl font-bold">User Guide</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Everything you need to know about using LeagueQL.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 gap-12">
        <aside className="hidden w-52 shrink-0 lg:flex lg:min-h-0 lg:flex-col">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            On this page
          </p>
          <nav className="min-h-0 flex-1 cursor-pointer space-y-0.5 overflow-y-auto overscroll-contain pr-2">
            {tocItems.map((item) => (
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

        <div className="min-w-0 flex-1 space-y-12 overflow-y-auto overscroll-contain pb-8 pr-2">
          {/* Getting Started */}
          <section>
            <SectionHeading id="getting-started">
              Getting Started
            </SectionHeading>
            <p className="text-muted-foreground leading-relaxed mb-6">
              This app is designed for a web browser, not a mobile browser.
              While efforts have been made to make the mobile experience closely
              reflect the web experience, your experience may vary on mobile
              devices. Currently, only redraft leagues are compatible with all
              functionalities of the app. If you have a dynasty league, you may
              find the two draft pages do not make much sense as the
              calculations are designed to evaluate redraft leagues.
            </p>

            <div className="space-y-6">
              <div>
                <SubHeading id="demo-mode">Demo Mode</SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Want to explore the app before connecting your own league?
                  Click <Kbd>View Demo</Kbd> on the landing page. A sample
                  league is pre-loaded so you can navigate every page. Click{' '}
                  <Kbd>Exit Demo</Kbd> in the sidebar to return to the landing
                  page and connect your own league.
                </p>
              </div>

              <div>
                <SubHeading id="authentication">Authentication</SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  LeagueQL uses Clerk for authentication. From the landing page,
                  click <Kbd>Connect Your League</Kbd> and use Clerk&apos;s form
                  to sign in using your email and password or Google login.
                  After signing in you are returned to the landing page.
                </p>
              </div>
            </div>
          </section>

          {/* Connecting a League */}
          <section>
            <SectionHeading id="connecting-a-league">
              Connecting a League
            </SectionHeading>
            <p className="text-muted-foreground leading-relaxed mb-8">
              On the landing page, select your platform (ESPN or Sleeper) and
              enter your league ID, then click <Kbd>Connect</Kbd>. What happens
              next depends on the platform:
            </p>

            <div className="space-y-8">
              <div>
                <SubHeading id="espn-leagues">ESPN</SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  If the league has already been onboarded, you are taken
                  straight to your dashboard (or, if you are not yet a member of
                  the private league, prompted to verify your membership; see{' '}
                  <SectionLink id="joining-an-espn-league">
                    Joining an ESPN League
                  </SectionLink>{' '}
                  ). If not, you are taken to a separate form to enter your ESPN
                  credentials and complete onboarding.
                </p>
                <img
                  src={espnOnboardFormScreenshot}
                  alt="The ESPN Onboard/Refresh League form with fields for League ID, Latest Season, SWID, and ESPN S2"
                  className="mb-4 w-full rounded-md border border-border"
                />
                <SubSubHeading id="espn-form-fields">Form Fields</SubSubHeading>
                <div className="mb-4">
                  <DocTable
                    headers={['Field', 'Description']}
                    rows={[
                      [
                        'League ID',
                        <>
                          The numeric ID in your ESPN fantasy URL (e.g.{' '}
                          <Kbd>?leagueId=12345</Kbd>)
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
                            Application → Cookies → fantasy.espn.com → SWID
                          </strong>
                        </>,
                      ],
                      [
                        'ESPN S2 Cookie',
                        'Found in the same location as SWID but under the name espn_s2',
                      ],
                    ]}
                  />
                </div>
                <Callout>
                  Your SWID and ESPN S2 cookies are only transmitted once over
                  HTTPS to fetch your data and are never stored by LeagueQL.
                </Callout>

                <div className="mt-6">
                  <SubSubHeading id="chrome-extension">
                    Chrome Extension
                  </SubSubHeading>
                </div>
                <p className="text-muted-foreground leading-relaxed mb-3">
                  Finding your SWID and ESPN S2 cookies by hand can be tedious.
                  The{' '}
                  <a
                    href={ESPN_EXTENSION_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline underline-offset-2 hover:text-primary/80"
                  >
                    LeagueQL ESPN Cookie Helper
                  </a>{' '}
                  Chrome extension reads those two cookies straight from your
                  browser and fills them into the form for you. Please note that
                  it is not required to use the extension; you can enter the
                  cookie values manually if you prefer.
                </p>
                <ol className="list-decimal pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                  <li>
                    Install the extension from the Chrome Web Store and log into{' '}
                    <strong className="text-foreground">
                      fantasy.espn.com
                    </strong>{' '}
                    in another browser tab.
                  </li>
                  <li>
                    On the Onboard/Refresh League form, click{' '}
                    <Kbd>Autofill cookies from ESPN</Kbd>. The extension reads
                    your ESPN cookies and populates the SWID and ESPN S2 fields
                    automatically.
                  </li>
                </ol>
                <Callout>
                  The extension reads only your <code>espn_s2</code> and{' '}
                  <code>SWID</code> cookies from ESPN and passes them to the
                  form; it never stores or transmits them anywhere else. If it
                  is not installed, you can fill the cookie fields in manually.
                </Callout>
              </div>

              <div>
                <SubHeading id="sleeper-leagues">Sleeper</SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Enter your league ID, then click <Kbd>Connect</Kbd>. After
                  onboarding is completed, you are redirected to your
                  league&apos;s dashboard.
                </p>
                <SubSubHeading id="sleeper-form-fields">
                  Form Fields
                </SubSubHeading>
                <div className="mb-4">
                  <DocTable
                    headers={['Field', 'Description']}
                    rows={[
                      [
                        'League ID',
                        <>
                          The numeric ID in your Sleeper league URL (e.g.{' '}
                          <Kbd>https://sleeper.com/leagues/12345</Kbd>)
                        </>,
                      ],
                    ]}
                  />
                </div>
              </div>

              <div>
                <SubHeading id="ownership-and-access">
                  League Ownership
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-3">
                  The first person to connect a league becomes its owner in
                  LeagueQL. Only the owner sees and can use the league&apos;s
                  management actions in the sidebar:
                </p>
                <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                  <li>Refresh League</li>
                  <li>Migrate League</li>
                  <li>Transfer Ownership</li>
                  <li>Delete League</li>
                </ul>
                <p className="text-muted-foreground leading-relaxed mb-8">
                  Everyone else (your leaguemates) can view the league dashboard
                  but not these actions.
                </p>

                <div className="space-y-8">
                  <div>
                    <SubSubHeading id="joining-an-espn-league">
                      Joining an ESPN League
                    </SubSubHeading>
                    <p className="text-muted-foreground leading-relaxed mb-3">
                      Because ESPN league data is private, leaguemates other
                      than the owner must prove they belong to the league before
                      they can view it. When you connect for the first time to
                      an onboarded ESPN league, you will see a{' '}
                      <strong className="text-foreground">
                        Verify your ESPN league membership
                      </strong>{' '}
                      prompt instead of the dashboard.
                    </p>
                    <img
                      src={espnVerifyMembershipScreenshot}
                      alt="The Join league dialog prompting for SWID and ESPN S2 cookies to verify ESPN league membership"
                      className="mb-4 w-full rounded-md border border-border"
                    />
                    <p>
                      Enter your SWID and ESPN S2 cookies or use the LeagueQL
                      ESPN Cookie Helper{' '}
                      <a
                        href={ESPN_EXTENSION_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline underline-offset-2 hover:text-primary/80"
                      >
                        extension
                      </a>{' '}
                      to verify your membership. If your cookies are valid, you
                      are added to the league as a member and the dashboard
                      unlocks immediately. If not, you will see
                      <Kbd>
                        We couldn&apos;t confirm you&apos;re in this ESPN
                        league.
                      </Kbd>
                    </p>
                    <br></br>
                  </div>

                  <div>
                    <SubSubHeading id="transferring-ownership">
                      Transferring Ownership
                    </SubSubHeading>
                    <p className="text-muted-foreground leading-relaxed mb-3">
                      Ownership can be handed to another member with a one-time
                      token:
                    </p>
                    <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                      <li>
                        <strong className="text-foreground">
                          Current owner:
                        </strong>{' '}
                        click <Kbd>Transfer Ownership</Kbd> in the sidebar, then{' '}
                        <Kbd>Generate token</Kbd>. Copy the token and share it
                        privately with the new owner.
                      </li>
                      <li>
                        <strong className="text-foreground">New owner:</strong>{' '}
                        click <Kbd>Claim Ownership</Kbd> in the sidebar, paste
                        the token, and click <Kbd>Claim ownership</Kbd>.
                        Ownership transfers right away; you gain the owner
                        actions and the previous owner becomes a regular member.
                      </li>
                    </ul>
                    <Callout variant="warning">
                      The token expires after 24 hours and can be used only
                      once; generating a new token invalidates any previous one.
                      Anyone with the token can claim ownership, so share it
                      privately. If a league&apos;s owner cannot be contacted,
                      contact{' '}
                      <a
                        href="mailto:support@leagueql.com"
                        className="text-primary underline underline-offset-2 hover:text-primary/80"
                      >
                        support@leagueql.com
                      </a>
                      .
                    </Callout>
                  </div>
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
                <strong className="text-foreground">LeagueQL logo</strong>:
                returns you to the landing page
              </li>
              <li>
                <strong className="text-foreground">Changelog, Docs</strong>:
                links to the changelog and user docs
              </li>
              <li>
                <strong className="text-foreground">
                  Dark/light mode toggle
                </strong>
                : toggle between dark mode and light mode, defaults to your
                system preferences
              </li>
            </ul>
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
                <SubSubHeading id="refresh-espn">ESPN</SubSubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Click the Refresh League button in the sidebar. This navigates
                  you to the league connection page where you can submit your
                  credentials again. The system detects the league already
                  exists and fetches the latest data for your league.
                </p>
                <SubSubHeading id="refresh-sleeper">Sleeper</SubSubHeading>
                <MinorHeading>Midseason Refreshes</MinorHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  You do not need to refresh your Sleeper league during the
                  active season. An automated process runs weekly every Tuesday
                  morning to update your league data.
                </p>
                <MinorHeading>New Season Refreshes</MinorHeading>
                <p className="text-muted-foreground leading-relaxed">
                  If refreshing for a new season, enter your new Sleeper league
                  ID as if you are connecting a new league (Sleeper league IDs
                  change each season). The system automatically associates the
                  new league ID with your existing history.
                </p>
              </div>

              <div>
                <SubHeading id="migrating-your-league">
                  Migrating Your League
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-4">
                  Use this when your league moves from one platform to another
                  in the offseason (ESPN → Sleeper or Sleeper → ESPN). Click
                  <Kbd>Migrate League</Kbd> in the sidebar settings.
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
                    Provide the league ID for the new platform. For ESPN, you
                    will also need to enter the latest season, SWID, and ESPN S2
                    cookies. See the{' '}
                    <SectionLink id="espn-form-fields">Form Fields</SectionLink>{' '}
                    section above for details on these fields and how to fill
                    them in.
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
                <div className="mt-4">
                  <Callout variant="warning">
                    <strong>Experimental feature</strong>: League migration
                    cannot be undone. All-time metrics will be recalculated to
                    reflect the merged history across both platforms.
                  </Callout>
                </div>
              </div>

              <div>
                <SubHeading id="switching-leagues">
                  Switching Leagues
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Click <Kbd>View Another League</Kbd> in the sidebar. You are
                  taken back to the landing page where you can enter a different
                  league ID.
                </p>
              </div>

              <div>
                <SubHeading id="deleting-a-league">
                  Deleting a League
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed">
                  Click <Kbd>Delete League</Kbd> at the bottom of the sidebar.
                  This permanently removes all stored data for the league from
                  LeagueQL&apos;s backend. This action cannot be undone.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
