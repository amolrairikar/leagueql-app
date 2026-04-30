import { DEMO_LEAGUE_ID, DEMO_PLATFORM } from './demo-constants';

export type Platform = 'ESPN' | 'SLEEPER';

export interface LeagueCookies {
  leagueId: string;
  platform: Platform;
  seasons: string[];
}

function readCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

function writeCookie(name: string, value: string, maxAge?: number): void {
  const age = maxAge !== undefined ? `; max-age=${maxAge}` : '';
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/${age}`;
}

function eraseCookie(name: string): void {
  document.cookie = `${name}=; path=/; max-age=0`;
}

export function getLeagueCookies(): LeagueCookies {
  const leagueId = readCookie('leagueId');
  const platform = (readCookie('leaguePlatform') || 'ESPN') as Platform;
  let seasons: string[] = [];
  try {
    const raw = readCookie('leagueSeasons');
    if (raw) seasons = JSON.parse(raw) as string[];
  } catch {
    // malformed cookie — fall back to empty
  }
  return { leagueId, platform, seasons };
}

export function setLeagueCookies(
  leagueId: string,
  platform: Platform,
  seasons: string[],
): void {
  writeCookie('leagueId', leagueId);
  writeCookie('leaguePlatform', platform);
  writeCookie('leagueSeasons', JSON.stringify(seasons));
}

export function clearLeagueCookies(): void {
  eraseCookie('leagueId');
  eraseCookie('leaguePlatform');
  eraseCookie('leagueSeasons');
}

export function setDemoMode(seasons: string[]): void {
  writeCookie('leagueId', DEMO_LEAGUE_ID, 86400);
  writeCookie('leaguePlatform', DEMO_PLATFORM, 86400);
  writeCookie('leagueSeasons', JSON.stringify(seasons), 86400);
  document.cookie = 'demo_mode=true; path=/; max-age=86400';
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
