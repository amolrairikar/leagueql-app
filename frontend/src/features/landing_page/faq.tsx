import { Link } from 'react-router-dom';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Kbd } from '@/components/ui/kbd';

interface FaqItem {
  q: string;
  a?: React.ReactNode;
  steps?: string[];
  note?: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    q: 'Why do I need to provide my ESPN cookies?',
    a: 'ESPN leagues are private and require logging in to ESPN to view. The SWID and ESPN S2 cookies provide the authentication required to fetch data. These cookies are not stored.',
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
    a: (
      <>
        If the page shows a timeout error, try again once as there may be an
        issue with the ESPN or Sleeper servers. If the issue persists, file a
        bug report with{' '}
        <a
          href="mailto:support@leagueql.com"
          className="text-primary underline underline-offset-2 hover:text-primary/80"
        >
          support@leagueql.com
        </a>{' '}
        and provide a screenshot + details so it can be investigated.
      </>
    ),
  },
  {
    q: 'My data looks outdated. How do I refresh it?',
    a: (
      <>
        For ESPN leagues, click <Kbd>Refresh League</Kbd> in the sidebar and
        re-submit your league credentials. Sleeper leagues will refresh
        automatically each week during the season.
      </>
    ),
  },
  {
    q: 'Can I connect more than one league?',
    a: (
      <>
        Yes. Use the <Kbd>View Another League</Kbd> option in the sidebar to
        view or onboard another league. Each league is stored independently.
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
        <Link
          to="/docs"
          className="text-primary underline underline-offset-2 hover:text-primary/80"
        >
          League Ownership
        </Link>{' '}
        for how ownership works and how to transfer it.
      </>
    ),
  },
  {
    q: 'My leaguemate onboarded our ESPN league. How do I view it?',
    a: (
      <>
        Enter the league ID and click <Kbd>Connect</Kbd>, then use the{' '}
        <Kbd>Verify membership</Kbd> prompt to confirm your ESPN cookies grant
        you access. Once verified the dashboard unlocks.
      </>
    ),
  },
];

export function Faq() {
  return (
    <Accordion
      type="single"
      collapsible
      className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-border bg-card"
    >
      {FAQ_ITEMS.map((item, i) => (
        <AccordionItem key={item.q} value={`faq-${i}`}>
          <AccordionTrigger>{item.q}</AccordionTrigger>
          <AccordionContent>
            {item.a}
            {item.steps && (
              <ol className="list-decimal space-y-1 pl-6">
                {item.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            )}
            {item.note && <p className="mt-2 text-sm italic">{item.note}</p>}
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
