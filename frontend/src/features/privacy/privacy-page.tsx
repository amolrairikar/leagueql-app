import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

const sections = [
  { id: 'overview', title: '1. Overview' },
  { id: 'data-we-collect', title: '2. Data We Collect' },
  { id: 'how-we-use', title: '3. How We Use Your Data' },
  { id: 'data-storage', title: '4. Data Storage' },
  { id: 'third-party', title: '5. Third-Party Services' },
  { id: 'data-sharing', title: '6. Data Sharing' },
  { id: 'data-retention', title: '7. Data Retention' },
  { id: 'your-rights', title: '8. Your Rights' },
  { id: 'security', title: '9. Security' },
  { id: 'contact', title: '10. Contact' },
];

export default function PrivacyPage() {
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
        onClick={() => navigate(-1)}
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
            <h1 className="text-4xl font-bold">Privacy Policy</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Last updated: April 25, 2026
            </p>
          </div>

          <section id="overview" className="space-y-3">
            <h2 className="text-2xl font-semibold">1. Overview</h2>
            <p className="text-muted-foreground leading-relaxed">
              LeagueQL ("we", "our", "us") is a tool that helps you analyze your
              fantasy football league history from ESPN and Sleeper platforms.
              We collect and process league data to provide you with different
              insights.
            </p>
          </section>

          <section id="data-we-collect" className="space-y-3">
            <h2 className="text-2xl font-semibold">2. Data We Collect</h2>
            <div className="space-y-4 text-muted-foreground leading-relaxed">
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  League Data (from ESPN/Sleeper APIs):
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
                    Email address and authentication credentials (managed by
                    Clerk)
                  </li>
                  <li>User profile information you choose to provide</li>
                </ul>
              </div>
            </div>
          </section>

          <section id="how-we-use" className="space-y-3">
            <h2 className="text-2xl font-semibold">3. How We Use Your Data</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>
                Display league history, standings, draft recaps, and matchups
              </li>
              <li>Enable comparisons and statistical analysis</li>
              <li>Refresh league data to keep information current</li>
            </ul>
          </section>

          <section id="data-storage" className="space-y-3">
            <h2 className="text-2xl font-semibold">4. Data Storage</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>All league data is stored in AWS</li>
              <li>
                Authentication is managed by Clerk (see their privacy policy).
                Clerk uses cookies for session management.
              </li>
              <li>
                ESPN cookies are only used temporarily to fetch private league
                data and are not stored on our servers
              </li>
            </ul>
          </section>

          <section id="third-party" className="space-y-3">
            <h2 className="text-2xl font-semibold">5. Third-Party Services</h2>
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
                <strong>AWS:</strong> Application hosting
              </li>
            </ul>
          </section>

          <section id="data-sharing" className="space-y-3">
            <h2 className="text-2xl font-semibold">6. Data Sharing</h2>
            <p className="text-muted-foreground leading-relaxed">
              We do not sell your data. League data is only used to provide the
              app's features.
            </p>
          </section>

          <section id="data-retention" className="space-y-3">
            <h2 className="text-2xl font-semibold">7. Data Retention</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>League data is retained until you request deletion</li>
              <li>You can request removal of your league data at any time</li>
            </ul>
          </section>

          <section id="your-rights" className="space-y-3">
            <h2 className="text-2xl font-semibold">8. Your Rights</h2>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground leading-relaxed">
              <li>View the data we have about your leagues</li>
              <li>Request deletion of your league data</li>
            </ul>
          </section>

          <section id="security" className="space-y-3">
            <h2 className="text-2xl font-semibold">9. Security</h2>
            <p className="text-muted-foreground leading-relaxed">
              We have implemented security measures to protect your data,
              including encryption in transit and at rest for stored data.
            </p>
          </section>

          <section id="contact" className="space-y-3">
            <h2 className="text-2xl font-semibold">10. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              For privacy inquiries or data deletion requests, contact us at
              arairikar1@gmail.com.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
