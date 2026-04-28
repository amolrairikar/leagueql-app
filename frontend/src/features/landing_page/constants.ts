import { FileText, Info } from 'lucide-react';

import draftRecapScreenshot from '@/assets/draft-recap-screenshot.png';
import managerComparisonScreenshot from '@/assets/manager-comparison-screenshot.png';
import managerHistoryScreenshot from '@/assets/manager-history-screenshot.png';
import matchupsScreenshot from '@/assets/matchups-screenshot.png';
import playoffBracketScreenshot from '@/assets/playoff-bracket-screenshot.png';
import playerRecordsScreenshot from '@/assets/player-records-screenshot.png';
import standingsScreenshot from '@/assets/standings-screenshot.png';
import { GitHubIcon } from '@/features/landing_page/github-icon';
import type {
  NavLinkItem,
  Slide,
  Feature,
} from '@/features/landing_page/types';

export const NAV_LINKS: NavLinkItem[] = [
  { label: 'GitHub', href: 'https://github.com/amolrairikar/leagueql-app', icon: GitHubIcon },
  { label: 'Changelog', href: 'https://github.com/amolrairikar/leagueql-app/blob/main/CHANGELOG.md', icon: FileText },
  { label: 'Docs', href: '#', icon: Info },
];

export const SLIDES: Slide[] = [
  {
    title: 'Standings',
    badge: 'League Table',
    url: 'leagueql.app/standings',
    caption: 'Current season standings',
    image: standingsScreenshot,
  },
  {
    title: 'Matchups',
    badge: 'Weekly Results',
    url: 'leagueql.app/matchups',
    caption: 'Weekly matchup results',
    image: matchupsScreenshot,
  },
  {
    title: 'Playoff Bracket',
    badge: 'Tournament',
    url: 'leagueql.app/playoff_bracket',
    caption: 'Visual playoff bracket',
    image: playoffBracketScreenshot,
  },
  {
    title: 'Manager Comparison',
    badge: 'Head-to-Head',
    url: 'leagueql.app/manager_comparison',
    caption: 'Compare any two managers across all seasons',
    image: managerComparisonScreenshot,
  },
  {
    title: 'Manager History',
    badge: 'All Seasons',
    url: 'leagueql.app/manager_history',
    caption: 'Individual manager performance over time',
    image: managerHistoryScreenshot,
  },
  {
    title: 'Draft Recap',
    badge: 'Draft Analysis',
    url: 'leagueql.app/draft_recap',
    caption: 'Draft picks and their season performance',
    image: draftRecapScreenshot,
  },
  {
    title: 'Player Records',
    badge: 'All-Time Best',
    url: 'leagueql.app/player_records',
    caption: 'Single-game and season player records',
    image: playerRecordsScreenshot,
  },
];

export const FEATURES: Feature[] = [
  {
    icon: '📜',
    title: 'Complete History',
    desc: 'Every season, every week, every score — pulled automatically from ESPN or Sleeper and organized chronologically.',
  },
  {
    icon: '⚔️',
    title: 'Rivalry Tracker',
    desc: 'See your all-time head-to-head record against every manager, including playoff matchups and average scoring.',
  },
  {
    icon: '🏆',
    title: 'Championship Timeline',
    desc: 'A visual hall of fame showing every champion, runner-up, and consolation bracket winner across all seasons.',
  },
  {
    icon: '📈',
    title: 'Scoring Trends',
    desc: 'Chart how your team — and the league — has evolved over the years, week by week and season over season.',
  },
  {
    icon: '🔖',
    title: 'League Records',
    desc: 'Single-week high scores, biggest blowouts, most unlucky losses — every record tracked and ranked automatically.',
  },
  {
    icon: '🔗',
    title: 'Instant Sync',
    desc: 'Connect your ESPN or Sleeper league in seconds. Full history imports automatically — no manual entry needed.',
  },
];

export const FOOTER_LINKS: string[] = [
  'About',
  'Privacy',
];
