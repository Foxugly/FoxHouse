import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Etape } from '../../core/vue';
import { vueDebut } from '../../../testing/vues';
import { DELAI_ETAPE, etapeAuPas, Relecture } from './relecture';

function etapes(n: number): Etape[] {
  return Array.from({ length: n }, (_, i) => ({ message: `Étape ${i + 1}`, vue: vueDebut() }));
}

describe('etapeAuPas', () => {
  it("rend l'étape du pas, puis null une fois les étapes passées", () => {
    const e = etapes(2);
    expect(etapeAuPas(e, 0)).toBe(e[0]);
    expect(etapeAuPas(e, 1)).toBe(e[1]);
    expect(etapeAuPas(e, 2)).toBeNull();
    expect(etapeAuPas([], 0)).toBeNull();
  });
});

describe('Relecture', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it(`montre une étape toutes les ${DELAI_ETAPE} ms, puis s'arrête`, () => {
    const r = new Relecture();
    const e = etapes(3);
    r.lancer(e);
    expect(r.etape()).toBe(e[0]);
    expect(r.enCours()).toBe(true);
    vi.advanceTimersByTime(DELAI_ETAPE - 1);
    expect(r.etape()).toBe(e[0]);
    vi.advanceTimersByTime(1);
    expect(r.etape()).toBe(e[1]);
    vi.advanceTimersByTime(DELAI_ETAPE);
    expect(r.etape()).toBe(e[2]);
    vi.advanceTimersByTime(DELAI_ETAPE);
    expect(r.etape()).toBeNull();
    expect(r.enCours()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('passer saute à la fin et coupe la minuterie', () => {
    const r = new Relecture();
    r.lancer(etapes(3));
    r.passer();
    expect(r.enCours()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("sans étape, il n'y a rien à rejouer", () => {
    const r = new Relecture();
    r.lancer([]);
    expect(r.enCours()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('une nouvelle relecture remplace la précédente', () => {
    const r = new Relecture();
    r.lancer(etapes(3));
    vi.advanceTimersByTime(DELAI_ETAPE);
    const suivantes = etapes(1);
    r.lancer(suivantes);
    expect(r.etape()).toBe(suivantes[0]);
    expect(vi.getTimerCount()).toBe(1);
  });
});
