import { Kbd } from '@/components/ui/kbd';
import {
  Callout,
  MinorHeading,
  SectionHeading,
  SectionLink,
  SubHeading,
  SubSubHeading,
} from '@/features/instructions/doc-components';

export function ManagingYourLeagueSection() {
  return (
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
          <MinorHeading>Manual Refresh</MinorHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            Click the <Kbd>Refresh League</Kbd> button in the sidebar. A dialog
            opens where you re-enter your ESPN cookies (or autofill them with
            the Chrome extension) and LeagueQL fetches the latest data for your
            league in place. The season is detected automatically, so you never
            enter it.
          </p>
          <div className="mb-4">
            <Callout>
              Each league can be refreshed manually at most once per week.
              Refreshing is also unavailable during the offseason or when your
              league is already up to date.
            </Callout>
          </div>
          <MinorHeading>Automatic Weekly Refresh (opt-in)</MinorHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            When you first connect an ESPN league on the landing page, or in the{' '}
            <Kbd>Refresh League</Kbd> dialog, you can check{' '}
            <Kbd>Enable automatic weekly refresh</Kbd>. When enabled, LeagueQL
            securely stores your ESPN cookies, encrypted, and refreshes your
            league automatically each week during the season, so you do not have
            to re-enter them. ESPN cookies expire periodically; when they do, we
            ask you to re-enter them to keep automatic refresh working. You can
            turn it off anytime with <Kbd>Turn Off Auto-Refresh</Kbd> in the
            sidebar. Your stored cookies are shared by all of your ESPN leagues,
            so they are removed once none of them has automatic refresh on.
          </p>
          <SubSubHeading id="refresh-sleeper">Sleeper</SubSubHeading>
          <MinorHeading>Midseason Refreshes</MinorHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            You do not need to refresh your Sleeper league during the active
            season. An automated process runs weekly every Tuesday morning to
            update your league data.
          </p>
          <MinorHeading>New Season Refreshes</MinorHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            When a new fantasy season starts, enter your new Sleeper league ID
            on the landing page as if you are connecting a new league (Sleeper
            league IDs change each season). The app automatically associates the
            new league ID with your existing history.
          </p>
          <SubSubHeading id="refresh-yahoo">Yahoo</SubSubHeading>
          <p className="text-muted-foreground leading-relaxed">
            Yahoo leagues refresh automatically each week during the season
            using your connected Yahoo account.
          </p>
        </div>

        <div>
          <SubHeading id="migrating-your-league">
            Migrating Your League
          </SubHeading>
          <p className="text-muted-foreground leading-relaxed mb-4">
            Use this when your league moves from one platform to another in the
            offseason. Click
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
              Review your existing league name, platform, and season history.
            </li>
            <li>
              <strong className="text-foreground">
                Enter new league details:
              </strong>{' '}
              Provide the league ID for the new platform. For ESPN, you will
              also need to enter the latest season, SWID, and ESPN S2 cookies.
              See the{' '}
              <SectionLink id="espn-form-fields">Form Fields</SectionLink>{' '}
              section above for details on these fields and how to fill them in.
            </li>
            <li>
              <strong className="text-foreground">Map managers:</strong> Match
              each manager to their account on the new platform. Managers who
              left can be marked as &quot;Not returning&quot; and their
              historical stats remain visible.
            </li>
            <li>
              <strong className="text-foreground">Preview & confirm:</strong>{' '}
              Review the migration summary and confirm. The migration runs in
              the background (typically ~1 minute).
            </li>
          </ol>
          <div className="mt-4">
            <Callout variant="warning">
              <strong>Experimental feature</strong>: League migration cannot be
              undone. All-time metrics will be recalculated to reflect the
              merged history across both platforms.
            </Callout>
          </div>
        </div>

        <div>
          <SubHeading id="switching-leagues">Switching Leagues</SubHeading>
          <p className="text-muted-foreground leading-relaxed">
            Click <Kbd>View Another League</Kbd> in the sidebar. You are taken
            back to the landing page where you can enter a different league ID.
          </p>
        </div>

        <div>
          <SubHeading id="deleting-a-league">Deleting a League</SubHeading>
          <p className="text-muted-foreground leading-relaxed">
            Click <Kbd>Delete League</Kbd> at the bottom of the sidebar. This
            permanently removes all stored data for the league from
            LeagueQL&apos;s backend. This action cannot be undone.
          </p>
        </div>
      </div>
    </section>
  );
}
