import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearAllLeagueCookies,
  clearEspnCookies,
  clearLeagueCookies,
  getLeagueCookies,
  isDemoMode,
  readCookie,
  setDemoMode,
  setLeagueCookies,
} from '../cookie-handler';

// ── Helpers ───────────────────────────────────────────────────────────────────

function clearAllCookies(): void {
  document.cookie.split(';').forEach((cookie) => {
    const name = cookie.split('=')[0].trim();
    if (name) document.cookie = `${name}=; max-age=0; path=/`;
  });
}

function clearAll(): void {
  clearAllCookies();
  window.localStorage.clear();
}

// ── readCookie ────────────────────────────────────────────────────────────────

describe('readCookie', () => {
  beforeEach(clearAll);

  it('returns the decoded value when the cookie exists', () => {
    document.cookie = 'myKey=hello';
    expect(readCookie('myKey')).toBe('hello');
  });

  it("returns '' when the cookie does not exist", () => {
    expect(readCookie('nonexistent')).toBe('');
  });

  it('URI-decodes the value', () => {
    document.cookie = `encoded=${encodeURIComponent('hello,world')}`;
    expect(readCookie('encoded')).toBe('hello,world');
  });

  it('returns the correct value when multiple cookies are set', () => {
    document.cookie = 'a=1';
    document.cookie = 'b=2';
    document.cookie = 'c=3';
    expect(readCookie('b')).toBe('2');
  });
});

// ── getLeagueCookies ──────────────────────────────────────────────────────────

describe('getLeagueCookies', () => {
  beforeEach(clearAll);

  it('returns leagueId, platform, and seasons from localStorage', () => {
    setLeagueCookies('123', 'ESPN', ['2022', '2023']);
    expect(getLeagueCookies()).toEqual({
      leagueId: '123',
      platform: 'ESPN',
      seasons: ['2022', '2023'],
    });
  });

  it('defaults platform to ESPN when stored value is unknown', () => {
    window.localStorage.setItem('leagueId', '99');
    window.localStorage.setItem('leaguePlatform', 'UNKNOWN');
    expect(getLeagueCookies().platform).toBe('ESPN');
  });

  it('returns empty seasons array when leagueSeasons is absent', () => {
    window.localStorage.setItem('leagueId', '99');
    window.localStorage.setItem('leaguePlatform', 'ESPN');
    expect(getLeagueCookies().seasons).toEqual([]);
  });

  it('returns empty seasons array and does not throw on malformed JSON', () => {
    window.localStorage.setItem('leagueId', '99');
    window.localStorage.setItem('leaguePlatform', 'ESPN');
    window.localStorage.setItem('leagueSeasons', 'not-json!');
    expect(() => getLeagueCookies()).not.toThrow();
    expect(getLeagueCookies().seasons).toEqual([]);
  });
});

// ── setLeagueCookies / clearLeagueCookies ─────────────────────────────────────

describe('setLeagueCookies / clearLeagueCookies', () => {
  beforeEach(clearAll);

  it('persists values readable by getLeagueCookies', () => {
    setLeagueCookies('777', 'SLEEPER', ['2021', '2022']);
    const result = getLeagueCookies();
    expect(result.leagueId).toBe('777');
    expect(result.platform).toBe('SLEEPER');
    expect(result.seasons).toEqual(['2021', '2022']);
  });

  it('clearLeagueCookies erases leagueId, leaguePlatform, and leagueSeasons', () => {
    setLeagueCookies('777', 'ESPN', ['2022']);
    clearLeagueCookies();
    expect(window.localStorage.getItem('leagueId')).toBeNull();
    expect(window.localStorage.getItem('leaguePlatform')).toBeNull();
    expect(window.localStorage.getItem('leagueSeasons')).toBeNull();
  });
});

// ── isDemoMode ────────────────────────────────────────────────────────────────

describe('isDemoMode', () => {
  beforeEach(clearAll);

  it('returns false when demo_mode cookie is not set', () => {
    expect(isDemoMode()).toBe(false);
  });

  it('returns true when demo_mode=true cookie is set', () => {
    document.cookie = 'demo_mode=true';
    expect(isDemoMode()).toBe(true);
  });

  it('returns false for a partial match (demo_mode=true-extra)', () => {
    // isDemoMode uses exact equality: row === 'demo_mode=true'
    document.cookie = 'demo_mode=true-extra';
    expect(isDemoMode()).toBe(false);
  });
});

// ── setDemoMode ───────────────────────────────────────────────────────────────

describe('setDemoMode', () => {
  beforeEach(clearAll);

  it('makes isDemoMode() return true', () => {
    setDemoMode(['2022', '2023']);
    expect(isDemoMode()).toBe(true);
  });

  it('sets league cookies to demo values', () => {
    setDemoMode(['2022', '2023', '2024']);
    const cookies = getLeagueCookies();
    expect(cookies.leagueId).toBe('888888888');
    expect(cookies.platform).toBe('SLEEPER');
    expect(cookies.seasons).toEqual(['2022', '2023', '2024']);
  });
});

// ── clearAllLeagueCookies ─────────────────────────────────────────────────────

describe('clearAllLeagueCookies', () => {
  beforeEach(clearAll);

  it('clears demo_mode and all league storage after setDemoMode', () => {
    setDemoMode(['2022', '2023']);
    clearAllLeagueCookies();
    expect(isDemoMode()).toBe(false);
    expect(window.localStorage.getItem('leagueId')).toBeNull();
    expect(window.localStorage.getItem('leaguePlatform')).toBeNull();
    expect(window.localStorage.getItem('leagueSeasons')).toBeNull();
  });
});

// ── clearEspnCookies ──────────────────────────────────────────────────────────

describe('clearEspnCookies', () => {
  beforeEach(clearAll);

  it('erases SWID and espn_s2 cookies', () => {
    document.cookie = 'SWID=swid-value';
    document.cookie = 'espn_s2=espn-s2-value';
    clearEspnCookies();
    expect(readCookie('SWID')).toBe('');
    expect(readCookie('espn_s2')).toBe('');
  });
});
