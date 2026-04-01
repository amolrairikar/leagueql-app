import { FileText, Info } from 'lucide-react';

import { GitHubIcon } from '@/features/landing_page/github-icon';
import type {
  NavLinkItem,
  Slide,
  Feature,
} from '@/features/landing_page/types';

export const NAV_LINKS: NavLinkItem[] = [
  { label: 'GitHub', href: '#', icon: GitHubIcon },
  { label: 'Changelog', href: '#', icon: FileText },
  { label: 'Docs', href: '#', icon: Info },
];

export const SLIDES: Slide[] = [
  {
    title: 'All-Time Records',
    badge: '2014 - 2024',
    url: 'leagueql.app/records',
    caption: 'All-time records, championship history & season scoring trends',
  },
  {
    title: 'Head-to-Head History',
    badge: 'All Seasons',
    url: 'leagueql.app/rivalries',
    caption: 'Head-to-head rivalries with win rates and playoff matchups',
  },
  {
    title: 'Season-by-Season',
    badge: 'Your Team',
    url: 'leagueql.app/history',
    caption: 'Your personal season-by-season history across all years',
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
  'GitHub',
  'Changelog',
  'Docs',
  'Privacy',
];
