import { describe, expect, it } from 'vitest';
import { indexRenforce, largeurCarte, pasCartes, positionsSieges } from './disposition';

describe('positionsSieges', () => {
  it('place le siège 0 en bas, le 1 à gauche et le 2 en haut (4 sièges)', () => {
    const p = positionsSieges(4, 1000, 600);
    expect(p[0].x).toBeCloseTo(500);
    expect(p[0].y).toBeGreaterThan(300);
    expect(p[1].x).toBeLessThan(500);
    expect(p[1].y).toBeCloseTo(300);
    expect(p[2].x).toBeCloseTo(500);
    expect(p[2].y).toBeLessThan(300);
    expect(p[3].x).toBeGreaterThan(500);
  });

  it('garde toutes les positions dans le rectangle de 1 à 10 sièges', () => {
    for (let n = 1; n <= 10; n++) {
      for (const p of positionsSieges(n, 1000, 600)) {
        expect(p.x).toBeGreaterThanOrEqual(0);
        expect(p.x).toBeLessThanOrEqual(1000);
        expect(p.y).toBeGreaterThanOrEqual(0);
        expect(p.y).toBeLessThanOrEqual(600);
      }
    }
  });
});

describe('largeurCarte', () => {
  it('est bornée entre 34 et 62', () => {
    expect(largeurCarte(100, 100)).toBe(34);
    expect(largeurCarte(5000, 5000)).toBe(62);
    expect(largeurCarte(900, 600)).toBeCloseTo(840 / 15);
  });
});

describe('pasCartes', () => {
  it('tient sur une rangée quand la place suffit', () => {
    const r = pasCartes(7, 50, 600);
    expect(r.rangees).toBe(1);
    expect(r.parRangee).toBe(7);
    expect(r.pas).toBeCloseTo(54);
  });

  it('passe à deux rangées quand une rangée ne suffit pas', () => {
    const r = pasCartes(22, 40, 330);
    expect(r.rangees).toBe(2);
    expect(r.parRangee).toBe(11);
    expect(r.pas).toBeGreaterThanOrEqual(0.42 * 40 * 0.8);
  });

  it('gère zéro ou une carte', () => {
    expect(pasCartes(0, 50, 600)).toEqual({ pas: 0, rangees: 1, parRangee: 0 });
    expect(pasCartes(1, 50, 600)).toEqual({ pas: 0, rangees: 1, parRangee: 1 });
  });
});

describe('indexRenforce', () => {
  it('est vrai sous 0,6 fois la largeur de carte', () => {
    expect(indexRenforce(20, 50)).toBe(true);
    expect(indexRenforce(30, 50)).toBe(false);
  });
});
