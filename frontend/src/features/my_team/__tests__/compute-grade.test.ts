import { describe, expect, it } from 'vitest';

import { computeGrades, letterForPercentile } from '../compute-grade';

import { standing } from './factories';

describe('compute-grade', () => {
  it('maps percentiles to letters at the band edges', () => {
    expect(letterForPercentile(98)).toBe('A+');
    expect(letterForPercentile(90)).toBe('A');
    expect(letterForPercentile(73)).toBe('B+');
    expect(letterForPercentile(58)).toBe('B');
    expect(letterForPercentile(40)).toBe('C+');
    expect(letterForPercentile(5)).toBe('D');
  });

  it('grades the strongest team highest and the weakest lowest', () => {
    const standings = [
      standing({
        team_id: '1',
        win_pct_vs_league: 0.9,
        total_pf: 1400,
        win_pct: 0.9,
      }),
      standing({
        team_id: '2',
        win_pct_vs_league: 0.5,
        total_pf: 1100,
        win_pct: 0.5,
      }),
      standing({
        team_id: '3',
        win_pct_vs_league: 0.1,
        total_pf: 900,
        win_pct: 0.1,
      }),
    ];
    const grades = computeGrades(standings, new Map());
    expect(grades.get('1')!.percentile).toBeGreaterThan(
      grades.get('3')!.percentile,
    );
    expect(grades.get('1')!.composite).toBeGreaterThan(
      grades.get('3')!.composite,
    );
  });

  it('grades an unlucky team (great scoring, poor record) above a lucky one', () => {
    // Team U: elite all-play + points, mediocre record. Team L: the inverse.
    const standings = [
      standing({
        team_id: 'U',
        win_pct_vs_league: 0.8,
        total_pf: 1400,
        win_pct: 0.45,
      }),
      standing({
        team_id: 'L',
        win_pct_vs_league: 0.4,
        total_pf: 1000,
        win_pct: 0.7,
      }),
      standing({
        team_id: 'M',
        win_pct_vs_league: 0.5,
        total_pf: 1150,
        win_pct: 0.5,
      }),
    ];
    const grades = computeGrades(standings, new Map());
    expect(grades.get('U')!.composite).toBeGreaterThan(
      grades.get('L')!.composite,
    );
  });

  it('treats a team missing efficiency data as league-median for that term', () => {
    const standings = [
      standing({ team_id: '1', total_pf: 1200 }),
      standing({ team_id: '2', total_pf: 1000 }),
    ];
    // No efficiency map entries → no crash, grades still produced.
    const grades = computeGrades(standings, new Map());
    expect(grades.size).toBe(2);
    expect(grades.get('1')!.letter).toBeTruthy();
  });
});
