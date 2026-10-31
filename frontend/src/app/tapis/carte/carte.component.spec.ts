import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { Carte } from '../../core/vue';
import { CarteComponent, RAPPORT_CARTE } from './carte.component';

function monter(
  carte: Carte,
  extra: Record<string, unknown> = {},
): ComponentFixture<CarteComponent> {
  const fixture = TestBed.createComponent(CarteComponent);
  fixture.componentRef.setInput('carte', carte);
  for (const [cle, valeur] of Object.entries(extra)) fixture.componentRef.setInput(cle, valeur);
  fixture.detectChanges();
  return fixture;
}

const racine = (f: ComponentFixture<CarteComponent>) => f.nativeElement as HTMLElement;
const texte = (f: ComponentFixture<CarteComponent>, sel: string) =>
  racine(f).querySelector(sel)?.textContent?.trim();

describe('CarteComponent', () => {
  it("une carte cachée n'a pas d'image", () => {
    const f = monter({ cachee: true });
    expect(racine(f).querySelector('img')).toBeNull();
    expect(racine(f).querySelector('.dos')).not.toBeNull();
  });

  it('une carte visible a une image et un alt en français', () => {
    const f = monter({ id: '10H-2', valeur: '10', enseigne: 'H' });
    const img = racine(f).querySelector('img')!;
    expect(img.getAttribute('src')).toBe('/cartes/webisso/10_of_hearts.svg');
    expect(img.alt).toBe('10 de cœur');
  });

  it('nomme les figures et les enseignes', () => {
    const f = monter({ id: 'AS-1', valeur: 'A', enseigne: 'S' });
    expect(racine(f).querySelector('img')!.alt).toBe('as de pique');
    const g = monter({ id: 'QC-1', valeur: 'Q', enseigne: 'C' });
    expect(racine(g).querySelector('img')!.alt).toBe('dame de trèfle');
  });

  it('un joker se lit « joker » et porte le badge de la carte remplacée', () => {
    const f = monter({ id: 'JK-1', joker: true, represente: '7C' });
    expect(racine(f).querySelector('img')!.alt).toBe('joker');
    expect(texte(f, '.badge')).toBe('7♣');
    const g = monter({ id: 'JK-2', joker: true, represente: 'K*' });
    expect(texte(g, '.badge')).toBe('R*');
  });

  it("un joker sans valeur représentée n'a pas de badge", () => {
    const f = monter({ id: 'JK-1', joker: true });
    expect(racine(f).querySelector('.badge')).toBeNull();
  });

  it("l'index n'apparaît qu'avec indexRenforce", () => {
    const carte = { id: '10H-2', valeur: '10', enseigne: 'H' };
    expect(texte(monter(carte), '.index')).toBeUndefined();
    const f = monter(carte, { indexRenforce: true });
    expect(texte(f, '.index')).toBe('10♥');
    expect(racine(f).querySelector('.index.rouge')).not.toBeNull();
  });

  it('la hauteur suit le rapport des images', () => {
    const f = monter({ cachee: true }, { largeur: 50 });
    expect(racine(f).style.width).toBe('50px');
    expect(parseFloat(racine(f).style.height)).toBeCloseTo(50 * RAPPORT_CARTE, 3);
  });
});
