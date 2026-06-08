import { Info, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import { isBillingEnabled } from '@/lib/feature-flags';

const TOC_ITEMS = [
  { id: 'getting-started', label: 'Getting Started', level: 1 },
  { id: 'demo-mode', label: 'Demo Mode', level: 2 },
  { id: 'authentication', label: 'Authentication', level: 2 },
  { id: 'connecting-a-league', label: 'Connecting a League', level: 1 },
  { id: 'espn-leagues', label: 'ESPN Leagues', level: 2 },
  { id: 'sleeper-leagues', label: 'Sleeper Leagues', level: 2 },
  { id: 'ownership-and-access', label: 'Ownership & Access', level: 2 },
  { id: 'the-league-owner', label: 'The League Owner', level: 3 },
  { id: 'joining-an-espn-league', label: 'Joining an ESPN League', level: 3 },
  { id: 'transferring-ownership', label: 'Transferring Ownership', level: 3 },
  { id: 'subscribing', label: 'Subscribing', level: 2 },
  { id: 'free-trial', label: 'Free Trial', level: 2 },
  { id: 'navigation', label: 'Navigation', level: 1 },
  { id: 'managing-your-league', label: 'Managing Your League', level: 1 },
  { id: 'refreshing-league-data', label: 'Refreshing League Data', level: 2 },
  { id: 'migrating-your-league', label: 'Migrating Your League', level: 2 },
  { id: 'switching-leagues', label: 'Switching Leagues', level: 2 },
  { id: 'managing-billing', label: 'Managing Billing', level: 2 },
  { id: 'deleting-a-league', label: 'Deleting a League', level: 2 },
  { id: 'faq-and-troubleshooting', label: 'FAQ & Troubleshooting', level: 1 },
] as const;

// Billing-related content is hidden when billing is feature-flagged off (FE-026):
// these TOC entries and this FAQ entry, plus the Subscribing / Free Trial /
// Managing Billing sections and the inline billing mentions in the prose.
const BILLING_TOC_IDS = new Set<string>([
  'subscribing',
  'free-trial',
  'managing-billing',
]);
const BILLING_FAQ_QUESTION = 'Why is there a subscription for the app?';

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
    note: 'With the LeagueQL ESPN Cookie Helper Chrome extension installed, you can skip these steps: just log into ESPN, then click "Autofill from ESPN" on the onboarding form.',
  },
  {
    q: 'The connection timed out. What happened?',
    a: 'If the page shows a timeout error, note the operation ID displayed and try again. If the issue persists, file a bug report with the operation ID so it can be investigated.',
  },
  {
    q: 'My data looks outdated. How do I refresh it?',
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
    a: "The subscription helps cover the cost of hosting the app and the time spent developing and maintaining it. It's billed per league, not per person. One person (the league owner) handles billing for the league, but league-mates are free to split that cost among themselves outside of the app. For a 10-person league it works out to about $0.39 per person per year.",
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
  {
    q: "Why don't I see the Refresh, Migrate, or Delete buttons?",
    a: (
      <>
        Those actions are available only to the league&apos;s owner, the person
        who first connected it. Everyone else can view the full dashboard but
        not manage the league. See{' '}
        <SectionLink id="ownership-and-access">
          Ownership &amp; Access
        </SectionLink>{' '}
        for how ownership works and how to transfer it.
      </>
    ),
  },
  {
    q: 'My leaguemate onboarded our ESPN league. How do I view it?',
    a: (
      <>
        Open the league, then use the <InlineCode>Verify membership</InlineCode>{' '}
        prompt to confirm your ESPN cookies grant you access. Once verified you
        become a member and the dashboard unlocks. Sleeper leagues are public,
        so no verification is needed.
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
  const billingEnabled = isBillingEnabled();
  const tocItems = billingEnabled
    ? TOC_ITEMS
    : TOC_ITEMS.filter((item) => !BILLING_TOC_IDS.has(item.id));
  const faqItems = billingEnabled
    ? FAQ_ITEMS
    : FAQ_ITEMS.filter((item) => item.q !== BILLING_FAQ_QUESTION);

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
              devices. Currently, only redraft leagues are supported.
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
            </div>
          </section>

          {/* Connecting a League */}
          <section>
            <SectionHeading id="connecting-a-league">
              Connecting a League
            </SectionHeading>
            <p className="text-muted-foreground leading-relaxed mb-4">
              On the landing page, select your platform (ESPN or Sleeper) and
              enter your league ID in the inline connect form, then submit. What
              happens next depends on the platform:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-8">
              <li>
                <strong className="text-foreground">Sleeper leagues:</strong>{' '}
                The league ID is all that is needed. The app fetches or onboards
                your league right from the landing page (no credentials
                required, as the underlying Sleeper API is read-only).
                Onboarding typically takes ~45 seconds, after which you are
                redirected to your league&apos;s home dashboard.
              </li>
              <li>
                <strong className="text-foreground">ESPN leagues:</strong> If
                the league has already been onboarded, you are taken straight to
                your dashboard (or, if you are not yet a member of the private
                league, prompted to verify your membership; see{' '}
                <SectionLink id="joining-an-espn-league">
                  Joining an ESPN League
                </SectionLink>{' '}
                below). If it is a new league, you are taken to a separate form
                to enter your ESPN credentials and complete onboarding.
              </li>
            </ul>

            <div className="space-y-8">
              <div>
                <SubHeading id="espn-leagues">ESPN Leagues</SubHeading>
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
                <SubHeading id="sleeper-leagues">Sleeper Leagues</SubHeading>
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

              <div>
                <SubHeading id="ownership-and-access">
                  Ownership &amp; Access
                </SubHeading>
                <p className="text-muted-foreground leading-relaxed mb-6">
                  Once you connect a league you become its{' '}
                  <strong>owner</strong>. Every league has a single owner, the
                  person who first connected it, who controls how the league is
                  managed{billingEnabled ? ' and billed' : ''}. Who can{' '}
                  <em>view</em> a league depends on the platform: Sleeper data
                  is public, so any signed-in user can view a Sleeper league,
                  while ESPN data is private, so only verified members of an
                  ESPN league can view it.
                </p>

                <div className="space-y-8">
                  <div>
                    <SubSubHeading id="the-league-owner">
                      The League Owner
                    </SubSubHeading>
                    <p className="text-muted-foreground leading-relaxed mb-3">
                      The first person to connect a league becomes its owner.
                      Only the owner sees and can use the league&apos;s
                      management actions in the sidebar:
                    </p>
                    <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                      <li>Refresh League</li>
                      <li>Migrate League</li>
                      {billingEnabled && (
                        <li>Manage Subscription / Subscribe (billing)</li>
                      )}
                      <li>Transfer Ownership</li>
                      <li>Delete League</li>
                    </ul>
                    <p className="text-muted-foreground leading-relaxed">
                      Everyone else who can view the league (your league-mates)
                      sees the full dashboard but not these actions.
                      {billingEnabled && (
                        <>
                          {' '}
                          If a league&apos;s subscription has lapsed, only the
                          owner is shown the Subscribe button; non-owners are
                          asked to have the owner subscribe.
                        </>
                      )}
                    </p>
                  </div>

                  <div>
                    <SubSubHeading id="joining-an-espn-league">
                      Joining an ESPN League
                    </SubSubHeading>
                    <p className="text-muted-foreground leading-relaxed mb-3">
                      Because ESPN league data is private, league-mates other
                      than the owner must prove they belong to the league before
                      they can view it. When you open an ESPN league you are not
                      yet a member of, you will see a{' '}
                      <strong className="text-foreground">
                        Verify your ESPN league membership
                      </strong>{' '}
                      prompt instead of the dashboard.
                    </p>
                    <ol className="list-decimal pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                      <li>
                        Make sure you are logged into ESPN in your browser (the
                        LeagueQL ESPN Cookie Helper extension makes this
                        seamless).
                      </li>
                      <li>
                        Click <InlineCode>Verify membership</InlineCode>.
                        LeagueQL checks your ESPN cookies against this specific
                        league.
                      </li>
                      <li>
                        If your cookies grant access, you are added to the
                        league&apos;s members and the dashboard unlocks
                        immediately. If they do not, you will see &quot;We
                        couldn&apos;t confirm you&apos;re in this ESPN
                        league.&quot;
                      </li>
                    </ol>
                    <Callout>
                      The owner never needs to verify; they are a member
                      automatically. Verification reuses the same SWID / ESPN S2
                      cookies as onboarding; they are used once to confirm
                      access and are never stored. Sleeper leagues are public,
                      so they never show this prompt.
                    </Callout>
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
                        click <InlineCode>Transfer Ownership</InlineCode> in the
                        sidebar, then <InlineCode>Generate token</InlineCode>.
                        Copy the token and share it privately with the new
                        owner.
                      </li>
                      <li>
                        <strong className="text-foreground">New owner:</strong>{' '}
                        click <InlineCode>Claim Ownership</InlineCode> in the
                        sidebar, paste the token, and click{' '}
                        <InlineCode>Claim ownership</InlineCode>. Ownership
                        transfers right away; you gain the owner actions and the
                        previous owner becomes a regular member.
                      </li>
                    </ul>
                    <Callout variant="warning">
                      The token expires after 24 hours and can be used only
                      once; generating a new token invalidates any previous one.
                      Anyone with the token can claim ownership, so share it
                      privately. If a league&apos;s owner is unavailable,
                      contact support.
                    </Callout>
                  </div>
                </div>
              </div>

              {billingEnabled && (
                <>
                  <div>
                    <SubHeading id="subscribing">Subscribing</SubHeading>
                    <p className="text-muted-foreground leading-relaxed mb-4">
                      LeagueQL is a paid product. Each connected league has its
                      own subscription, billed securely by Stripe; LeagueQL
                      never sees or stores your card details. Onboarding and
                      exploring demo mode are free, but a subscription is
                      required to view a connected league&apos;s analytics.
                    </p>
                    <p className="text-muted-foreground leading-relaxed mb-4">
                      Subscribing happens right after you onboard a league. A
                      newly connected league starts without an active
                      subscription, so once onboarding completes its analytics
                      pages are replaced with a paywall. Click{' '}
                      <InlineCode>Subscribe</InlineCode> there, or{' '}
                      <InlineCode>Manage Subscription</InlineCode> in the
                      sidebar, to open Stripe&apos;s secure checkout page. After
                      payment you are returned to your league&apos;s home
                      dashboard and access is restored automatically.
                    </p>
                    <Callout>
                      Have a promotion code? Enter it in the{' '}
                      <strong className="text-foreground">
                        Add promotion code
                      </strong>{' '}
                      field on the Stripe checkout page to apply a discount.
                    </Callout>
                  </div>

                  <div>
                    <SubHeading id="free-trial">Free Trial</SubHeading>
                    <p className="text-muted-foreground leading-relaxed">
                      Each league gets a 14 day free trial the first time it is
                      subscribed, so you can try LeagueQL with your
                      league&apos;s data before being charged. The trial is
                      granted once per league: re-subscribing a league that has
                      already used its trial, including after deleting and
                      re-connecting it, starts billing immediately with no
                      second trial. Trials are independent across different
                      leagues, so each league you connect gets its own.
                    </p>
                  </div>
                </>
              )}
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
            <p className="text-muted-foreground leading-relaxed">
              At the bottom of the sidebar you will find league management
              options: refresh your league, migrate to another platform, switch
              to view another league,{' '}
              {billingEnabled && 'manage your subscription, '}transfer
              ownership, and delete the current league. Most of these are
              available to owners only. See{' '}
              <SectionLink id="ownership-and-access">
                Ownership &amp; Access
              </SectionLink>{' '}
              above.
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
                  If refreshing for a new season, enter your new Sleeper league
                  ID as if you are connecting a new league (Sleeper league IDs
                  change each season). The backend automatically associates the
                  new league ID with your existing history.
                </p>
              </div>

              <div>
                <SubHeading id="migrating-your-league">
                  Migrating Your League
                </SubHeading>
                <Callout variant="warning">
                  <strong className="text-foreground">
                    Experimental feature
                  </strong>
                  : League migration cannot be undone. All-time metrics will be
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

              {billingEnabled && (
                <div>
                  <SubHeading id="managing-billing">
                    Managing Billing
                  </SubHeading>
                  <p className="text-muted-foreground leading-relaxed mb-4">
                    Click <InlineCode>Manage Subscription</InlineCode> in the
                    sidebar to open the billing dialog. From there you can
                    launch the Stripe Billing Portal to update your payment
                    method or cancel the subscription. LeagueQL shows a reminder
                    dot on the <InlineCode>Manage Subscription</InlineCode> icon
                    when a league&apos;s subscription is within 14 days of
                    expiring.
                  </p>
                  <Callout variant="warning">
                    <strong className="text-foreground">
                      Cancellation is immediate.
                    </strong>{' '}
                    Canceling ends the subscription right away and access to
                    that league&apos;s analytics is revoked at once; you are not
                    billed again, and there is no remaining paid period after
                    canceling.
                  </Callout>
                </div>
              )}

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
              {faqItems.map((item) => (
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
