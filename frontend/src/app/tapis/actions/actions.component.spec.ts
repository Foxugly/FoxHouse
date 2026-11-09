import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { Action, VueTable } from '../../core/vue';
import { vueDebut, vueEnAttente } from '../../../testing/vues';
import { Selection } from '../selection';
import { ActionsComponent, contraintes } from './actions.component';

function monter(
  vue: VueTable,
  selection: Selection = { cartes: [], cible: null },
  occupe = false,
): ComponentFixture<ActionsComponent> {
  const fixture = TestBed.createComponent(ActionsComponent);
  fixture.componentRef.setInput('vue', vue);
  fixture.componentRef.setInput('selection', selection);
  fixture.componentRef.setInput('occupe', occupe);
  fixture.detectChanges();
  return fixture;
}

const racine = (f: ComponentFixture<ActionsComponent>) => f.nativeElement as HTMLElement;
const boutons = (f: ComponentFixture<ActionsComponent>) =>
  Array.from(racine(f).querySelectorAll<HTMLButtonElement>('button'));
const bouton = (f: ComponentFixture<ActionsComponent>, libelle: string) =>
  boutons(f).find((b) => b.textContent?.trim() === libelle)!;

/** Les ids des n premières cartes de la main du joueur. */
function cartesDuJoueur(vue: VueTable, n: number): string[] {
  return vue.zones
    .find((z) => z.siege === vue.sieges[0].id)!
    .cartes.slice(0, n)
    .map((c) => ('id' in c ? c.id : ''));
}

describe('ActionsComponent', () => {
  it('quand le jeu attend le joueur : « À toi de jouer » et un bouton par action', () => {
    const vue = vueEnAttente();
    const f = monter(vue);
    expect(racine(f).classList).toContain('a-toi');
    expect(racine(f).querySelector('.etat')?.textContent?.trim()).toBe('À toi de jouer');
    expect(boutons(f).map((b) => b.textContent?.trim())).toEqual(vue.actions.map((a) => a.libelle));
  });

  it("sans action, la barre dit qu'on attend les autres et ne montre aucun bouton", () => {
    const f = monter({ ...vueEnAttente(), actions: [] });
    expect(racine(f).classList).not.toContain('a-toi');
    expect(racine(f).querySelector('.etat')?.textContent?.trim()).toBe(
      'En attente des autres joueurs…',
    );
    expect(boutons(f)).toEqual([]);
  });

  it('partie terminée : la barre le dit', () => {
    const f = monter({ ...vueEnAttente(), actions: [], terminee: true });
    expect(racine(f).querySelector('.etat')?.textContent?.trim()).toBe('Partie terminée');
  });

  it('une action de 3 cartes au moins est désactivée avec 2 cartes, active avec 3', () => {
    const vue = vueEnAttente();
    const action = vue.actions.find((a) => a.cartes_min === 3)!;
    const f2 = monter(vue, { cartes: cartesDuJoueur(vue, 2), cible: null });
    expect(bouton(f2, action.libelle).disabled).toBe(true);
    const f3 = monter(vue, { cartes: cartesDuJoueur(vue, 3), cible: null });
    expect(bouton(f3, action.libelle).disabled).toBe(false);
  });

  it('un bouton désactivé montre ce qui manque, relié par aria-describedby', () => {
    const vue = vueEnAttente();
    const action = vue.actions.find((a) => a.cartes_min === 3)!;
    const f = monter(vue, { cartes: cartesDuJoueur(vue, 2), cible: null });
    const b = bouton(f, action.libelle);
    const id = b.getAttribute('aria-describedby')!;
    expect(id).toBeTruthy();
    const raison = racine(f).querySelector(`[id="${id}"]`)!;
    expect(raison.textContent?.trim()).toBe('3 à 13 cartes');
    expect(raison.closest('.action')).toBe(b.closest('.action'));

    const g = monter(vue, { cartes: cartesDuJoueur(vue, 3), cible: null });
    expect(bouton(g, action.libelle).getAttribute('aria-describedby')).toBeNull();
    expect(bouton(g, action.libelle).closest('.action')!.querySelector('.raison')).toBeNull();
  });

  it("une action directe n'a pas de bouton : une consigne la remplace", () => {
    const base = vueEnAttente();
    const action = base.actions.find((a) => a.cartes_min === 1 && a.cartes_max === 1)!;
    const f = monter({ ...base, actions: [{ ...action, direct: true }] });
    expect(boutons(f)).toEqual([]);
    expect(racine(f).querySelector('.consigne')?.textContent?.trim()).toBe(
      `${action.libelle} : un clic sur une carte suffit.`,
    );
  });

  it("occupé (requête ou relecture), ce n'est pas à toi : aucun bouton", () => {
    const f = monter(vueDebut(), { cartes: [], cible: null }, true);
    expect(racine(f).classList).not.toContain('a-toi');
    expect(boutons(f)).toEqual([]);
  });

  it("le clic émet l'action", () => {
    const vue = vueDebut();
    const f = monter(vue);
    const recues: Action[] = [];
    f.componentInstance.agir.subscribe((a) => recues.push(a));
    boutons(f)[0].click();
    expect(recues).toEqual([vue.actions[0]]);
  });

  it('les contraintes de sélection se lisent en français', () => {
    const action = (cartes_min: number, cartes_max: number, cible: null | 'groupe' = null) => ({
      id: 'x',
      libelle: 'X',
      cartes_min,
      cartes_max,
      cible,
    });
    expect(contraintes(action(0, 0))).toBe('');
    expect(contraintes(action(1, 1))).toBe('1 carte');
    expect(contraintes(action(2, 2))).toBe('2 cartes');
    expect(contraintes(action(0, 4))).toBe("jusqu'à 4 cartes");
    expect(contraintes(action(3, 13))).toBe('3 à 13 cartes');
    expect(contraintes(action(1, 1, 'groupe'))).toBe('1 carte et un groupe');
    expect(contraintes(action(0, 0, 'groupe'))).toBe('un groupe');
  });
});
