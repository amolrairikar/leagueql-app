import TocPageLayout, { type TocItem } from '@/components/toc-page-layout';

const sections: TocItem[] = [
  { id: 'overview', label: '1. Overview' },
  { id: 'data-we-collect', label: '2. Data We Collect & Store' },
  { id: 'third-party', label: '3. Third-Party Services' },
  { id: 'data-sharing', label: '4. Data Sharing, Retention & Security' },
  { id: 'your-rights', label: '5. Your Rights' },
  { id: 'contact', label: '6. Contact Us' },
];

export default function PrivacyPage() {
  return (
    <TocPageLayout
      title="Privacy Policy"
      subtitle="Last updated: September 20, 2026"
      tocLabel="Table of Contents"
      tocItems={sections}
    >
      <section id="overview" className="space-y-3">
        <h2 className="text-2xl font-semibold">1. Overview</h2>
        <p className="text-muted-foreground leading-relaxed">
          LeagueQL (&quot;we&quot;, &quot;our&quot;, &quot;us&quot;) is a tool
          that helps you analyze your fantasy football league history from ESPN,
          Sleeper, and Yahoo platforms. We collect and process league data to
          provide you with different insights.
        </p>
      </section>

      <section id="data-we-collect" className="space-y-3">
        <h2 className="text-2xl font-semibold">2. Data We Collect & Store</h2>
        <div className="space-y-4 text-muted-foreground leading-relaxed">
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              League Data (from ESPN/Sleeper/Yahoo APIs):
            </h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Team names, logos, and owner display names</li>
              <li>Matchup results, scores, and lineups</li>
              <li>Season standings and playoff brackets</li>
              <li>Draft picks and player statistics</li>
              <li>Transaction history</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              User Authentication Data (via Clerk):
            </h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                Email address and authentication credentials (managed by Clerk)
              </li>
              <li>User profile information you choose to provide</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              ESPN Cookies (for private ESPN leagues):
            </h3>
            <p className="mb-2">
              To read a private ESPN league we need your ESPN <code>SWID</code>{' '}
              and <code>espn_s2</code> cookies. By default we use them only to
              fetch your league data for that request and do{' '}
              <strong>not</strong> store them. If you turn on{' '}
              <strong>automatic weekly refresh</strong> for an ESPN league, we
              then store those cookies so we can refresh it on your behalf:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                Your ESPN cookies are stored <strong>encrypted at rest</strong>{' '}
                and are never written to logs, shown in the app, or included in
                API responses.
              </li>
              <li>
                They are used only to refresh your ESPN league data on your
                behalf, and are never sold or shared with anyone.
              </li>
              <li>
                They are removed when you turn off automatic refresh for your
                last ESPN league or delete your league data. ESPN cookies also
                expire on their own, after which we ask you to re-enter them.
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              Yahoo OAuth Tokens (for Yahoo leagues):
            </h3>
            <p className="mb-2">
              Yahoo does not offer a public read-only data feed the way ESPN and
              Sleeper do, so connecting a Yahoo league uses Yahoo&apos;s
              official OAuth sign-in. This means we <strong>do</strong> store
              your Yahoo authorization:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                We store the OAuth access and refresh tokens Yahoo issues after
                you authorize LeagueQL. We never receive or store your Yahoo
                password.
              </li>
              <li>
                These tokens are stored encrypted at rest and are never written
                to logs, shown in the app, or included in API responses.
              </li>
              <li>
                We use them only to fetch and refresh your Yahoo league data on
                your behalf. They are never sold or shared with anyone.
              </li>
              <li>
                You can disconnect at any time: your stored Yahoo tokens are
                removed when you request deletion of your league data, and you
                can also revoke LeagueQL&apos;s access from your Yahoo account
                settings.
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              How We Store It:
            </h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>All league data is stored in AWS</li>
              <li>
                User account data is managed by Clerk (see their privacy
                policy). Clerk uses cookies for session management.
              </li>
              <li>
                ESPN cookies are used temporarily to fetch private league data
                and are not stored on our servers unless you enable automatic
                weekly refresh, in which case they are stored encrypted at rest
                and used only to refresh your league
              </li>
              <li>
                Yahoo OAuth tokens are stored, but encrypted at rest, and used
                only to fetch and refresh your Yahoo league data
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              ESPN Chrome Extension:
            </h3>
            <p>
              We offer an optional Chrome extension, &quot;LeagueQL ESPN Cookie
              Helper,&quot; that auto-fills your ESPN cookies into our
              onboarding and refresh forms. The extension does not store or
              transmit your cookies to us; it only fills them into the form on
              your device. See the{' '}
              <a
                href="/extension-privacy"
                className="text-foreground underline underline-offset-4"
              >
                Chrome Extension Privacy Policy
              </a>{' '}
              for details.
            </p>
          </div>
        </div>
      </section>

      <section id="third-party" className="space-y-3">
        <h2 className="text-2xl font-semibold">3. Third-Party Services</h2>
        <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
          <li>
            <strong>Clerk:</strong> Handles user authentication
          </li>
          <li>
            <strong>ESPN API:</strong> Source of ESPN fantasy football data
          </li>
          <li>
            <strong>Sleeper API:</strong> Source of Sleeper fantasy football
            data
          </li>
          <li>
            <strong>Yahoo Fantasy API:</strong> Source of Yahoo fantasy football
            data, accessed via Yahoo OAuth
          </li>
          <li>
            <strong>AWS:</strong> Application backend hosting
          </li>
          <li>
            <strong>Cloudflare:</strong> Website hosting (Cloudflare Pages)
          </li>
        </ul>
      </section>

      <section id="data-sharing" className="space-y-3">
        <h2 className="text-2xl font-semibold">
          4. Data Sharing, Retention & Security
        </h2>
        <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
          <li>
            We do not sell your data. League data is only used to provide the
            app&apos;s features.
          </li>
          <li>League data is retained until you request deletion</li>
          <li>You can request removal of your league data at any time</li>
          <li>
            We have implemented security measures to protect your data,
            including encryption in transit and at rest for stored data
          </li>
        </ul>
      </section>

      <section id="your-rights" className="space-y-3">
        <h2 className="text-2xl font-semibold">5. Your Rights</h2>
        <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
          <li>View the data we have about your leagues</li>
          <li>Request deletion of your league data</li>
        </ul>
      </section>

      <section id="contact" className="space-y-3">
        <h2 className="text-2xl font-semibold">6. Contact Us</h2>
        <p className="text-muted-foreground leading-relaxed">
          For any additional questions regarding the privacy policy, contact us
          at{' '}
          <a
            href="mailto:support@leagueql.com"
            className="font-medium underline underline-offset-4"
          >
            support@leagueql.com
          </a>
        </p>
      </section>
    </TocPageLayout>
  );
}
