import { Kbd } from '@/components/ui/kbd';
import {
  SectionHeading,
  SubHeading,
} from '@/features/instructions/doc-components';

export function GettingStartedSection() {
  return (
    <section>
      <SectionHeading id="getting-started">Getting Started</SectionHeading>
      <p className="text-muted-foreground leading-relaxed mb-6">
        This app is designed for a web browser, not a mobile browser. While
        efforts have been made to make the mobile experience closely reflect the
        web experience, your experience may vary on mobile devices. Currently,
        only redraft leagues are compatible with all functionalities of the app.
        If you have a dynasty league, you may find the draft pages do not make
        much sense as the calculations are designed to evaluate redraft leagues.
      </p>

      <div className="space-y-6">
        <div>
          <SubHeading id="demo-mode">Demo Mode</SubHeading>
          <p className="text-muted-foreground leading-relaxed">
            Want to explore the app before connecting your own league? Click{' '}
            <Kbd>View Demo</Kbd> on the landing page. A sample league is
            pre-loaded so you can navigate every page. Click{' '}
            <Kbd>Exit Demo</Kbd> in the sidebar to return to the landing page
            and connect your own league.
          </p>
        </div>

        <div>
          <SubHeading id="authentication">Authentication</SubHeading>
          <p className="text-muted-foreground leading-relaxed">
            LeagueQL uses Clerk for authentication. From the landing page, click{' '}
            <Kbd>Connect</Kbd> and use Clerk&apos;s form to sign in using your
            email and password or Google login. After signing in you are
            returned to the landing page.
          </p>
        </div>
      </div>
    </section>
  );
}
