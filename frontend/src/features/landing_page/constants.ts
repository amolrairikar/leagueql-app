import {
  Bookmark,
  Compass,
  Cpu,
  FileText,
  History,
  Info,
  Link2,
  Shuffle,
  Swords,
  TrendingUp,
  Trophy,
} from 'lucide-react';

import draftRecapScreenshot from '@/assets/draft-recap-screenshot.png';
import espnLogo from '@/assets/espn-logo.svg';
import managerComparisonScreenshot from '@/assets/manager-comparison-screenshot.png';
import managerHistoryScreenshot from '@/assets/manager-history-screenshot.png';
import matchupBoxscoreScreenshot from '@/assets/matchup-boxscore-screenshot.png';
import matchupsScreenshot from '@/assets/matchups-screenshot.png';
import playerRecordsScreenshot from '@/assets/player-records-screenshot.png';
import sleeperLogo from '@/assets/sleeper-logo.svg';
import standingsScreenshot from '@/assets/standings-screenshot.png';
import type {
  NavLinkItem,
  Slide,
  Feature,
  HowStep,
  Platform,
} from '@/features/landing_page/types';

export const NAV_LINKS: NavLinkItem[] = [
  { label: 'Changelog', href: '/changelog', icon: FileText, external: false },
  { label: 'Docs', href: '/docs', icon: Info, external: false },
];

export const PLATFORMS: Platform[] = [
  { name: 'ESPN', logo: espnLogo },
  { name: 'Sleeper', logo: sleeperLogo },
];

export const SLIDES: Slide[] = [
  {
    title: 'Standings',
    url: 'leagueql.app/standings',
    caption: 'Current season standings',
    image: standingsScreenshot,
  },
  {
    title: 'Matchups',
    url: 'leagueql.app/matchups',
    caption: 'Weekly matchup results',
    image: matchupsScreenshot,
  },
  {
    title: 'Matchup Box Scores',
    url: 'leagueql.app/matchups',
    caption: 'Full matchup box scores',
    image: matchupBoxscoreScreenshot,
  },
  {
    title: 'Manager Comparison',
    url: 'leagueql.app/manager_comparison',
    caption: 'Compare any two managers across all seasons',
    image: managerComparisonScreenshot,
  },
  {
    title: 'Manager History',
    url: 'leagueql.app/manager_history',
    caption: "Track an individual manager's performance",
    image: managerHistoryScreenshot,
  },
  {
    title: 'Player Records',
    url: 'leagueql.app/player_records',
    caption: 'Single-game and season player records',
    image: playerRecordsScreenshot,
  },
  {
    title: 'Draft Recap',
    url: 'leagueql.app/draft_recap',
    caption: 'Draft picks and their season performance',
    image: draftRecapScreenshot,
  },
];

export const FEATURES: Feature[] = [
  {
    icon: History,
    title: 'Complete History',
    desc: 'Every season, every week, every score. Currently supported integrations include ESPN and Sleeper.',
  },
  {
    icon: Swords,
    title: 'Rivalry Tracker',
    desc: 'See your all-time head-to-head record against every manager, from the guaranteed win to the manager who always has your number.',
  },
  {
    icon: Trophy,
    title: 'Championship Timeline',
    desc: 'A visual hall of fame showing every champion across all seasons.',
  },
  {
    icon: TrendingUp,
    title: 'Team Trends',
    desc: 'Chart how your team rankings have fluctuated throughout the years. Drill into your matchups for a particular season.',
  },
  {
    icon: Bookmark,
    title: 'League Records',
    desc: 'Every record tracked and ranked automatically: single-week high scores, biggest blowouts, most unlucky losses.',
  },
  {
    icon: Shuffle,
    title: 'Platform Migration',
    desc: 'Switched fantasy platforms? Use our league migration wizard to preserve your full all-time history across platforms.',
  },
];

export const HOW_STEPS: HowStep[] = [
  {
    step: 'STEP 1',
    icon: Link2,
    title: 'Connect your league',
    desc: "Paste your Sleeper or ESPN league ID. Private ESPN leagues need a quick one-time access step; we'll walk you through it.",
  },
  {
    step: 'STEP 2',
    icon: Cpu,
    title: 'We crunch every season',
    desc: 'LeagueQL pulls your full history and computes standings, records, rivalries, and trends.',
  },
  {
    step: 'STEP 3',
    icon: Compass,
    title: 'Explore the story',
    desc: 'Jump between seasons, settle debates, and relive every moment, all in one place.',
  },
];

export const FOOTER_LINKS: string[] = ['About', 'Privacy', 'GitHub'];
