import { describe, expect, it } from 'vitest';
import { Action } from '../core/vue';
import { actionActivable, basculer, choisirCible, Selection } from './selection';

const vide: Selection = { cartes: [], cible: null };
const action = (min: number, max: number, cible: null | 'groupe' = null): Action => ({
  id: 'a',
  libelle: 'A',
  cartes_min: min,
  cartes_max: max,
  cible,
});

describe('selection', () => {
  it('basculer ajoute puis retire une carte, sans muter', () => {
    const s1 = basculer(vide, 'c1');
    expect(s1.cartes).toEqual(['c1']);
    expect(vide.cartes).toEqual([]);
    const s2 = basculer(basculer(s1, 'c2'), 'c1');
    expect(s2.cartes).toEqual(['c2']);
  });

  it('choisirCible remplace la cible', () => {
    expect(choisirCible(vide, 'g1').cible).toBe('g1');
    expect(choisirCible({ cartes: ['c1'], cible: 'g1' }, null)).toEqual({ cartes: ['c1'], cible: null });
  });

  it('actionActivable respecte les bornes de cartes', () => {
    const a = action(3, 13);
    expect(actionActivable(a, { cartes: ['a', 'b'], cible: null })).toBe(false);
    expect(actionActivable(a, { cartes: ['a', 'b', 'c'], cible: null })).toBe(true);
    expect(actionActivable(a, { cartes: Array(14).fill('x'), cible: null })).toBe(false);
  });

  it('une action à cible groupe exige une cible', () => {
    const a = action(1, 1, 'groupe');
    expect(actionActivable(a, { cartes: ['a'], cible: null })).toBe(false);
    expect(actionActivable(a, { cartes: ['a'], cible: 'g1' })).toBe(true);
  });
});
