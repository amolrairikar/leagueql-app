import { ArrowLeft } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';

const releases = [
  {
    version: '1.0.0',
    date: '2025-05-31',
    added: [
      'Season standings from each past + current season and season superlative awards',
      'All historical league matchups + box scores',
      'Playoff brackets from each season',
      'Head-to-head comparison of any two managers',
      "Year-to-year history of each manager's performance",
      'Recap of draft picks and grades',
      'All-time fantasy player performance records',
      'All-time fantasy team performance records',
      'League migration: track all-time metrics even if your fantasy league migrates platforms',
    ],
  },
];

export default function ChangelogPage() {
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="container mx-auto max-w-3xl pt-16 pb-8 px-4">
      <Button
        variant="ghost"
        onClick={() => void navigate(-1)}
        className="mb-6 cursor-pointer"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <div className="mb-10">
        <h1 className="text-4xl font-bold">Changelog</h1>
        <p className="text-sm text-muted-foreground mt-2">
          All notable changes to LeagueQL are documented here.
        </p>
      </div>

      <div className="space-y-10">
        {releases.map((release) => (
          <div key={release.version} className="space-y-4">
            <div className="flex items-baseline gap-3">
              <h2 className="text-2xl font-semibold">[{release.version}]</h2>
              <span className="text-sm text-muted-foreground">
                {release.date}
              </span>
            </div>
            {release.added && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Added
                </h3>
                <ul className="list-disc pl-6 space-y-1 text-muted-foreground leading-relaxed">
                  {release.added.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
