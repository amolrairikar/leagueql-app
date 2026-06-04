import { ArrowLeft } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';

const sections = [
  { id: 'overview', title: '1. Overview' },
  { id: 'single-purpose', title: '2. Single Purpose' },
  { id: 'data-we-handle', title: '3. Data We Handle' },
  { id: 'how-it-works', title: '4. How It Works' },
  { id: 'permissions', title: '5. Permissions' },
  { id: 'storage-sharing', title: '6. Storage & Sharing' },
  { id: 'security', title: '7. Security' },
  { id: 'contact', title: '8. Contact' },
];

export default function ExtensionPrivacyPage() {
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

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

      <div className="flex gap-10">
        <aside className="hidden md:block w-52 shrink-0">
          <div className="sticky top-8 space-y-1">
            <p className="text-sm font-semibold mb-3">Table of Contents</p>
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollToSection(section.id)}
                className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-1 cursor-pointer"
              >
                {section.title}
              </button>
            ))}
          </div>
        </aside>

        <div className="flex-1 space-y-8">
          <div>
            <h1 className="text-4xl font-bold">
              ESPN Cookie Helper Extension Privacy Policy
            </h1>
            <p className="text-sm text-muted-foreground mt-2">
              Last updated: May 29, 2026
            </p>
          </div>

          <section id="overview" className="space-y-3">
            <h2 className="text-2xl font-semibold">1. Overview</h2>
            <p className="text-muted-foreground leading-relaxed">
              This policy describes how the &quot;LeagueQL ESPN Cookie
              Helper&quot; Chrome extension (&quot;the extension&quot;) handles
              your data. The extension is published by LeagueQL (&quot;we&quot;,
              &quot;our&quot;, &quot;us&quot;) as a convenience for connecting a
              private ESPN fantasy football league to LeagueQL. This policy
              covers only the browser extension. Data handled by the LeagueQL
              web application after it is received is governed by our main{' '}
              <a
                href="/privacy"
                className="text-foreground underline underline-offset-4"
              >
                Privacy Policy
              </a>
              .
            </p>
          </section>

          <section id="single-purpose" className="space-y-3">
            <h2 className="text-2xl font-semibold">2. Single Purpose</h2>
            <p className="text-muted-foreground leading-relaxed">
              The extension has a single purpose: to read your ESPN
              authentication cookies while you are logged in to ESPN and
              auto-fill them into the LeagueQL onboarding or refresh form, so
              you do not have to copy and paste them manually. The extension
              performs no other function.
            </p>
          </section>

          <section id="data-we-handle" className="space-y-3">
            <h2 className="text-2xl font-semibold">3. Data We Handle</h2>
            <div className="space-y-4 text-muted-foreground leading-relaxed">
              <p>
                The extension reads two ESPN cookies, which together act as your
                ESPN login session credentials:
              </p>
              <ul className="list-disc pl-6 space-y-1">
                <li>
                  <strong>SWID</strong> &mdash; your ESPN account identifier
                </li>
                <li>
                  <strong>espn_s2</strong> &mdash; your ESPN session token
                </li>
              </ul>
              <p>
                These are classified as{' '}
                <strong>authentication information</strong>. The extension does
                not read any other cookies, browsing history, personal
                information, or activity. It collects no analytics and contains
                no tracking code.
              </p>
            </div>
          </section>

          <section id="how-it-works" className="space-y-3">
            <h2 className="text-2xl font-semibold">4. How It Works</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>
                When you click &quot;Autofill from ESPN&quot; on a LeagueQL
                page, the extension reads your SWID and espn_s2 cookies from
                ESPN.
              </li>
              <li>
                It passes those values directly to the LeagueQL page open in
                your browser tab. The values never leave your device except as
                part of your interaction with LeagueQL.
              </li>
              <li>
                The extension itself has no server and makes no network requests
                of its own. It does not send your data to the extension&apos;s
                developer or any third party.
              </li>
            </ul>
          </section>

          <section id="permissions" className="space-y-3">
            <h2 className="text-2xl font-semibold">5. Permissions</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>
                <strong>cookies</strong> &mdash; required to read your SWID and
                espn_s2 cookies.
              </li>
              <li>
                <strong>Host access to espn.com</strong> &mdash; scopes cookie
                access to ESPN only; the extension cannot read cookies from any
                other site.
              </li>
              <li>
                The extension only injects its bridge script on LeagueQL pages
                (leagueql.com), so your ESPN cookies can only ever be relayed to
                LeagueQL.
              </li>
            </ul>
          </section>

          <section id="storage-sharing" className="space-y-3">
            <h2 className="text-2xl font-semibold">6. Storage & Sharing</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>
                The extension does not store your cookies. Values are read and
                handed off in the moment you trigger autofill.
              </li>
              <li>
                We do not sell your data, and we do not use or transfer it for
                any purpose unrelated to the extension&apos;s single purpose.
              </li>
              <li>
                Once the cookies reach LeagueQL, they are used only to fetch
                your private league data and are not stored on our servers, as
                described in our main{' '}
                <a
                  href="/privacy"
                  className="text-foreground underline underline-offset-4"
                >
                  Privacy Policy
                </a>
                .
              </li>
            </ul>
          </section>

          <section id="security" className="space-y-3">
            <h2 className="text-2xl font-semibold">7. Security</h2>
            <p className="text-muted-foreground leading-relaxed">
              The extension limits cookie access to ESPN and only communicates
              with LeagueQL pages over your browser&apos;s secure same-origin
              messaging. It performs no remote code execution and loads no code
              from external servers.
            </p>
          </section>

          <section id="contact" className="space-y-3">
            <h2 className="text-2xl font-semibold">8. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              For privacy inquiries related to the extension, contact us at{' '}
              <a
                href="mailto:support@leagueql.com"
                className="font-medium underline underline-offset-4"
              >
                support@leagueql.com
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
