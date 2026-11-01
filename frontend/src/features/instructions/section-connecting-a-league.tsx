import { Kbd } from '@/components/ui/kbd';
import {
  Callout,
  DocTable,
  SectionHeading,
  SectionLink,
  SubHeading,
  SubSubHeading,
} from '@/features/instructions/doc-components';
import { ESPN_EXTENSION_URL } from '@/lib/espn-extension';

export function ConnectingALeagueSection() {
  return (
    <section>
      <SectionHeading id="connecting-a-league">
        Connecting a League
      </SectionHeading>
      <p className="text-muted-foreground leading-relaxed mb-8">
        On the landing page, select your platform (ESPN, Sleeper, or Yahoo) and
        enter your league ID, then click <Kbd>Connect</Kbd>. What happens next
        depends on the platform:
      </p>

      <div className="space-y-8">
        <div>
          <SubHeading id="espn-leagues">ESPN</SubHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            If the league has already been onboarded, you are taken straight to
            your dashboard (or, for private leagues, told how to join it with an
            invite link from the owner; see{' '}
            <SectionLink id="joining-a-private-league">
              Joining a Private League
            </SectionLink>{' '}
            ). If not, SWID and ESPN S2 fields appear on the landing page for
            you to enter and connect your league.
          </p>
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
            Your SWID and ESPN S2 cookies are transmitted once over HTTPS to
            fetch your data. They are not stored by LeagueQL unless you enable
            automatic weekly refresh for the league, in which case they are
            stored encrypted so LeagueQL can refresh it for you. One set of
            stored cookies is shared by all of your ESPN leagues, and it is
            removed once none of them has automatic refresh on.
          </Callout>

          <div className="mt-6">
            <SubSubHeading id="chrome-extension">
              Chrome Extension
            </SubSubHeading>
          </div>
          <p className="text-muted-foreground leading-relaxed mb-3">
            Finding your SWID and ESPN S2 cookies by hand can be tedious. The{' '}
            <a
              href={ESPN_EXTENSION_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:text-primary/80"
            >
              LeagueQL ESPN Cookie Helper
            </a>{' '}
            Chrome extension reads those two cookies straight from your browser
            and fills them into the form for you. Please note that it is not
            required to use the extension; you can enter the cookie values
            manually if you prefer.
          </p>
          <ol className="list-decimal pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
            <li>
              Install the extension from the Chrome Web Store and log into{' '}
              <strong className="text-foreground">fantasy.espn.com</strong> in
              another browser tab.
            </li>
            <li>
              Wherever the SWID and ESPN S2 fields appear, click{' '}
              <Kbd>Autofill cookies from ESPN</Kbd>. The extension reads your
              ESPN cookies and populates the SWID and ESPN S2 fields
              automatically.
            </li>
          </ol>
          <Callout>
            The extension reads only your <code>espn_s2</code> and{' '}
            <code>SWID</code> cookies from ESPN and passes them to the form; it
            never stores or transmits them anywhere else. If you do not wish to
            install it, you can fill those fields in manually.
          </Callout>
        </div>

        <div>
          <SubHeading id="sleeper-leagues">Sleeper</SubHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            Enter your league ID, then click <Kbd>Connect</Kbd>. After
            onboarding is completed, you are redirected to your league&apos;s
            dashboard.
          </p>
          <SubSubHeading id="sleeper-form-fields">Form Fields</SubSubHeading>
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
          <SubHeading id="yahoo-leagues">Yahoo</SubHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            Yahoo leagues connect through Yahoo&apos;s official sign-in (OAuth),
            so there are no cookies to copy. Select{' '}
            <strong className="text-foreground">Yahoo</strong>, enter your
            league ID, and click <Kbd>Connect</Kbd>:
          </p>
          <ol className="list-decimal pl-6 space-y-2 text-muted-foreground leading-relaxed mb-4">
            <li>
              A pop-up opens with Yahoo&apos;s consent screen. Sign in to Yahoo
              (if you are not already) and click{' '}
              <strong className="text-foreground">Agree</strong> to let LeagueQL
              read your fantasy data.
            </li>
            <li>
              Yahoo redirects you back to LeagueQL, where onboarding resumes
              automatically. You will see the same progress bar as a Sleeper
              connect while we pull your league history, then land on your
              dashboard.
            </li>
          </ol>
          <Callout>
            You only authorize once. After your Yahoo account is linked,
            connecting more Yahoo leagues (or reconnecting later) skips the
            consent screen and onboards in place. If your Yahoo authorization is
            ever revoked or expires, LeagueQL will prompt you to reconnect.
          </Callout>
          <p className="text-muted-foreground leading-relaxed mt-4 mb-3">
            LeagueQL never sees your Yahoo password. It stores only the OAuth
            tokens Yahoo issues, encrypted, and uses them solely to fetch and
            refresh your league data. See the{' '}
            <a
              href="/privacy"
              className="text-primary underline underline-offset-2 hover:text-primary/80"
            >
              Privacy Policy
            </a>{' '}
            for details.
          </p>
          <SubSubHeading id="yahoo-form-fields">Form Fields</SubSubHeading>
          <div className="mb-4">
            <DocTable
              headers={['Field', 'Description']}
              rows={[
                [
                  'League ID',
                  <>
                    The numeric league ID in your Yahoo fantasy URL (e.g.{' '}
                    <Kbd>https://football.fantasysports.yahoo.com/f1/12345</Kbd>{' '}
                    → <Kbd>12345</Kbd>)
                  </>,
                ],
              ]}
            />
          </div>
        </div>

        <div>
          <SubHeading id="league-ownership">League Ownership</SubHeading>
          <p className="text-muted-foreground leading-relaxed mb-3">
            The first person to connect a league becomes its owner in LeagueQL.
            Only the owner sees and can use the league&apos;s management actions
            in the sidebar:
          </p>
          <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
            <li>Refresh League (ESPN only)</li>
            <li>Turn Off Auto-Refresh (ESPN only)</li>
            <li>Migrate League</li>
            <li>Transfer Ownership</li>
            <li>Invite Leaguemates (ESPN and Yahoo only)</li>
            <li>Delete League</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mb-8">
            Everyone else (your leaguemates) can view the league dashboard but
            not these actions.
          </p>

          <div className="space-y-8">
            <div>
              <SubSubHeading id="joining-a-private-league">
                Joining a Private League
              </SubSubHeading>
              <p className="text-muted-foreground leading-relaxed mb-3">
                ESPN and Yahoo league data is private, so leaguemates other than
                the owner join through an invite link the owner shares. The
                steps are the same on both platforms. Sleeper leagues are
                public, so anyone can view them without an invite.
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                <li>
                  <strong className="text-foreground">Owner:</strong> open the
                  league in LeagueQL, click <Kbd>Invite Leaguemates</Kbd> in the
                  sidebar, then <Kbd>Create invite link</Kbd>. Copy the link and
                  share it with your leaguemates.
                </li>
                <li>
                  <strong className="text-foreground">Leaguemate:</strong> open
                  the link the owner sent and sign into LeagueQL. You are added
                  to the league as a member and the dashboard unlocks
                  immediately.
                </li>
              </ul>
              <Callout variant="warning">
                Anyone with the link can view the league, so share it only with
                your leaguemates. The link stays valid until the owner creates a
                new one, which revokes the previous link. If a league&apos;s
                owner cannot be contacted, contact{' '}
                <a
                  href="mailto:support@leagueql.com"
                  className="text-primary underline underline-offset-2 hover:text-primary/80"
                >
                  support@leagueql.com
                </a>
                .
              </Callout>
              <br></br>
            </div>

            <div>
              <SubSubHeading id="transferring-ownership">
                Transferring Ownership
              </SubSubHeading>
              <p className="text-muted-foreground leading-relaxed mb-3">
                Ownership can be handed to another member with a one-time token:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed mb-3">
                <li>
                  <strong className="text-foreground">Current owner:</strong>{' '}
                  click <Kbd>Transfer Ownership</Kbd> in the sidebar, then{' '}
                  <Kbd>Generate token</Kbd>. Copy the token and share it
                  privately with the new owner.
                </li>
                <li>
                  <strong className="text-foreground">New owner:</strong> click{' '}
                  <Kbd>Claim Ownership</Kbd> in the sidebar, paste the token,
                  and click <Kbd>Claim ownership</Kbd>. Ownership transfers
                  right away; you gain the owner actions and the previous owner
                  becomes a regular member.
                </li>
              </ul>
              <Callout variant="warning">
                The token expires after 24 hours and can be used only once;
                generating a new token invalidates any previous one. Anyone with
                the token can claim ownership, so share it privately. If a
                league&apos;s owner cannot be contacted, contact{' '}
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
  );
}
