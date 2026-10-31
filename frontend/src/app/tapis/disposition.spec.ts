import { describe, expect, it } from 'vitest';
import {
  Cadre,
  indexRenforce,
  largeurCarte,
  pasCartes,
  placerCentre,
  positionsSieges,
} from './disposition';

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

  it('ajoute des rangées quand deux ne suffisent pas, sans jamais sortir de la largeur', () => {
    for (const [nb, dispo] of [
      [14, 100],
      [22, 100],
      [22, 60],
    ]) {
      const cw = 34;
      const r = pasCartes(nb, cw, dispo);
      expect(r.rangees).toBeGreaterThan(2);
      expect(r.rangees).toBe(Math.ceil(nb / r.parRangee));
      expect(r.pas).toBeGreaterThanOrEqual(0.42 * cw * 0.8);
      expect(cw + (r.parRangee - 1) * r.pas).toBeLessThanOrEqual(dispo + 1e-9);
    }
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

describe('placerCentre', () => {
  const chevauche = (a: Cadre, b: Cadre) =>
    a.gauche < b.droite && b.gauche < a.droite && a.haut < b.bas && b.haut < a.bas;

  it('sur une table large, garde la bande du milieu sans toucher les sièges', () => {
    const sieges: Cadre[] = [
      { gauche: 300, droite: 700, haut: 460, bas: 560 },
      { gauche: 40, droite: 200, haut: 200, bas: 320 },
      { gauche: 800, droite: 960, haut: 200, bas: 320 },
    ];
    const c = placerCentre(sieges, 1000, 600);
    expect(c.droite - c.gauche).toBeGreaterThanOrEqual(400);
    expect(c.bas - c.haut).toBeGreaterThan(200);
    for (const s of sieges) expect(chevauche(c, s)).toBe(false);
  });

  it('sur une table étroite et haute, passe sous les sièges des côtés', () => {
    // Mesures relevées sur un téléphone de 360 px, 3 sièges.
    const sieges: Cadre[] = [
      { gauche: 47, droite: 266, haut: 501, bas: 607 },
      { gauche: 0, droite: 111, haut: 155, bas: 257 },
      { gauche: 202, droite: 313, haut: 147, bas: 264 },
    ];
    const c = placerCentre(sieges, 313, 664);
    expect(c.droite - c.gauche).toBeGreaterThan(200);
    expect(c.bas - c.haut).toBeGreaterThan(150);
    for (const s of sieges) expect(chevauche(c, s)).toBe(false);
  });

  it('un siège en haut au milieu repousse le centre vers le bas', () => {
    const haut: Cadre = { gauche: 400, droite: 600, haut: 20, bas: 200 };
    const c = placerCentre([haut], 1000, 600);
    expect(c.haut).toBeGreaterThan(200);
  });

  it('sur une table étroite pleine de sièges, garde au moins une rangée de cartes en hauteur', () => {
    // 10 sièges serrés qui ne laissent aucun espace vertical libre.
    const sieges: Cadre[] = Array.from({ length: 10 }, (_, i) => ({
      gauche: 0,
      droite: 328,
      haut: i * 52,
      bas: i * 52 + 60,
    }));
    const c = placerCentre(sieges, 328, 520, 90);
    expect(c.bas - c.haut).toBeCloseTo(90);
    expect(c.haut).toBeGreaterThanOrEqual(0);
    expect(c.bas).toBeLessThanOrEqual(520);
  });
});
