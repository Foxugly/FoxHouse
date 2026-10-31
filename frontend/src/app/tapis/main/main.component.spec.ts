import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { Carte, CarteVisible } from '../../core/vue';
import { MainComponent } from './main.component';

const VALEURS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
const SEPT: CarteVisible = { id: '7H-1', valeur: '7', enseigne: 'H' };

function cartes(nb: number): CarteVisible[] {
  return Array.from({ length: nb }, (_, i) => ({
    id: `${VALEURS[i % 13]}H-${Math.floor(i / 13) + 1}`,
    valeur: VALEURS[i % 13],
    enseigne: 'H',
  }));
}

function monter(
  liste: Carte[],
  largeurDispo: number,
  cw: number,
  extra: Record<string, unknown> = {},
): ComponentFixture<MainComponent> {
  const fixture = TestBed.createComponent(MainComponent);
  fixture.componentRef.setInput('cartes', liste);
  fixture.componentRef.setInput('largeurDispo', largeurDispo);
  fixture.componentRef.setInput('cw', cw);
  for (const [cle, valeur] of Object.entries(extra)) fixture.componentRef.setInput(cle, valeur);
  fixture.detectChanges();
  return fixture;
}

const racine = (f: ComponentFixture<MainComponent>) => f.nativeElement as HTMLElement;
const places = (f: ComponentFixture<MainComponent>) =>
  Array.from(racine(f).querySelectorAll<HTMLElement>('.place'));

describe('MainComponent', () => {
  it('22 cartes dans 330 px : toutes dans la boîte, sur 2 rangées, index renforcé', () => {
    const f = monter(cartes(22), 330, 34);
    const p = places(f);
    expect(p).toHaveLength(22);
    for (const el of p) {
      expect(parseFloat(el.style.left)).toBeGreaterThanOrEqual(0);
      expect(parseFloat(el.style.left) + 34).toBeLessThanOrEqual(330);
    }
    expect(new Set(p.map((el) => el.style.top)).size).toBe(2);
    expect(racine(f).querySelectorAll('.index')).toHaveLength(22);
  });

  it('une main aérée tient sur une rangée sans index', () => {
    const f = monter(cartes(5), 400, 50);
    expect(new Set(places(f).map((el) => el.style.top)).size).toBe(1);
    expect(racine(f).querySelector('.index')).toBeNull();
  });

  it("un clic émet basculer avec l'id de la carte", () => {
    const f = monter([SEPT], 300, 50, { selectionnable: true });
    const recus: string[] = [];
    f.componentInstance.basculer.subscribe((id) => recus.push(id));
    places(f)[0].click();
    expect(recus).toEqual(['7H-1']);
  });

  it('Entrée et Espace font de même', () => {
    const f = monter([SEPT], 300, 50, { selectionnable: true });
    const recus: string[] = [];
    f.componentInstance.basculer.subscribe((id) => recus.push(id));
    const el = places(f)[0];
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    el.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
    expect(recus).toEqual(['7H-1', '7H-1']);
    expect(el.getAttribute('role')).toBe('button');
    expect(el.getAttribute('tabindex')).toBe('0');
  });

  it("sans selectionnable, rien n'est cliquable", () => {
    const f = monter([SEPT], 300, 50);
    const recus: string[] = [];
    f.componentInstance.basculer.subscribe((id) => recus.push(id));
    places(f)[0].click();
    expect(recus).toEqual([]);
    expect(places(f)[0].getAttribute('role')).toBeNull();
  });

  it('une carte sélectionnée est soulevée et aria-pressed', () => {
    const f = monter(cartes(3), 300, 50, {
      selectionnable: true,
      selection: { cartes: ['2H-1'], cible: null },
    });
    const p = places(f);
    expect(p[1].classList).toContain('soulevee');
    expect(p[1].getAttribute('aria-pressed')).toBe('true');
    expect(p[0].getAttribute('aria-pressed')).toBe('false');
  });

  it('une carte cachée ne se sélectionne pas', () => {
    const f = monter([{ cachee: true }], 300, 50, { selectionnable: true });
    const recus: string[] = [];
    f.componentInstance.basculer.subscribe((id) => recus.push(id));
    places(f)[0].click();
    expect(recus).toEqual([]);
    expect(places(f)[0].getAttribute('role')).toBeNull();
  });
});
