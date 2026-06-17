import { DEMO_LEAGUE_ID, DEMO_PLATFORM } from './demo-constants';

export type Platform = 'ESPN' | 'SLEEPER';

export interface LeagueCookies {
  leagueId: string;
  platform: Platform;
  seasons: string[];
}

export function readCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(match.indexOf('=') + 1)) : '';
}

const COOKIE_FLAGS = `; path=/; SameSite=Strict${import.meta.env.PROD ? '; Secure' : ''}`;

function eraseCookie(name: string): void {
  document.cookie = `${name}=${COOKIE_FLAGS}; max-age=0`;
}

function isPlatform(value: string): value is Platform {
  return value === 'ESPN' || value === 'SLEEPER';
}

export function getLeagueCookies(): LeagueCookies {
  const leagueId = window.localStorage.getItem('leagueId') ?? '';
  const rawPlatform = window.localStorage.getItem('leaguePlatform') ?? '';
  const platform: Platform = isPlatform(rawPlatform) ? rawPlatform : 'ESPN';
  let seasons: string[] = [];
  try {
    const raw = window.localStorage.getItem('leagueSeasons');
    if (raw) seasons = JSON.parse(raw) as string[];
  } catch {
    // malformed value — fall back to empty
  }
  return { leagueId, platform, seasons };
}

export function setLeagueCookies(
  leagueId: string,
  platform: Platform,
  seasons: string[],
): void {
  window.localStorage.setItem('leagueId', leagueId);
  window.localStorage.setItem('leaguePlatform', platform);
  window.localStorage.setItem('leagueSeasons', JSON.stringify(seasons));
}

export function clearLeagueCookies(): void {
  window.localStorage.removeItem('leagueId');
  window.localStorage.removeItem('leaguePlatform');
  window.localStorage.removeItem('leagueSeasons');
}

export function setDemoMode(seasons: string[]): void {
  window.localStorage.setItem('leagueId', DEMO_LEAGUE_ID);
  window.localStorage.setItem('leaguePlatform', DEMO_PLATFORM);
  window.localStorage.setItem('leagueSeasons', JSON.stringify(seasons));
  document.cookie = `demo_mode=true${COOKIE_FLAGS}; max-age=86400`;
}

export function clearEspnCookies(): void {
  eraseCookie('SWID');
  eraseCookie('espn_s2');
}

export function clearAllLeagueCookies(): void {
  clearLeagueCookies();
  eraseCookie('demo_mode');
}

export function isDemoMode(): boolean {
  return document.cookie.split('; ').some((row) => row === 'demo_mode=true');
}
