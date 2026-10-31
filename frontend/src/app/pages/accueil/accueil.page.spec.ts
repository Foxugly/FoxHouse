import { Component } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DescriptionJeu } from '../../core/vue';
import { jeuAvecOptions, jeuSansOption } from '../../../testing/jeux';
import { vueFactice } from '../../../testing/vues';
import { AccueilPage, joueursParDefaut, valeursParDefaut } from './accueil.page';

@Component({ template: '' })
class PageVide {}

let http: HttpTestingController;

beforeEach(() => {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([
        { path: '', component: AccueilPage },
        { path: 'partie', component: PageVide },
      ]),
    ],
  });
  http = TestBed.inject(HttpTestingController);
});

afterEach(() => http.verify());

/** Répond aux deux GET de l'accueil. */
function repondre(jeux: DescriptionJeu[], courante: unknown = null): void {
  http.expectOne('/api/jeux/').flush(jeux);
  const requete = http.expectOne('/api/parties/courante/');
  if (courante) requete.flush(courante);
  else requete.flush(null, { status: 204, statusText: 'No Content' });
}

function monter(jeux: DescriptionJeu[] = [jeuAvecOptions()], courante?: unknown) {
  const fixture = TestBed.createComponent(AccueilPage);
  fixture.detectChanges();
  repondre(jeux, courante);
  fixture.detectChanges();
  return fixture;
}

const racine = (f: ComponentFixture<unknown>) => f.nativeElement as HTMLElement;
const champ = <T extends HTMLElement>(f: ComponentFixture<unknown>, code: string) =>
  racine(f).querySelector<T>(`[data-option="${code}"]`)!;
const commencer = (f: ComponentFixture<unknown>) =>
  Array.from(racine(f).querySelectorAll<HTMLButtonElement>('button')).find(
    (b) => b.textContent?.trim() === 'Commencer',
  )!;

function changer(element: HTMLInputElement | HTMLSelectElement): void {
  element.dispatchEvent(new Event('change'));
}

describe('valeurs par défaut', () => {
  it('prennent le défaut de chaque option et le minimum + 1 joueurs, borné par le maximum', () => {
    expect(valeursParDefaut(jeuAvecOptions())).toEqual({
      as: 'bas1_haut11',
      ouverture_suite_sans_joker: false,
      penalite_joker: 20,
      manches: 5,
    });
    expect(joueursParDefaut(jeuAvecOptions())).toBe(3);
    expect(joueursParDefaut(jeuSansOption())).toBe(3);
  });
});

describe('AccueilPage', () => {
  it('génère le formulaire depuis la description du jeu', () => {
    const f = monter();
    const as = champ<HTMLSelectElement>(f, 'as');
    expect(as.tagName).toBe('SELECT');
    expect(Array.from(as.options).map((o) => o.textContent?.trim())).toEqual([
      '1 en bas de suite, 11 ailleurs',
      'Toujours 1',
      'Toujours 11',
    ]);
    expect(as.selectedIndex).toBe(0);
    const ouverture = champ<HTMLInputElement>(f, 'ouverture_suite_sans_joker');
    expect(ouverture.type).toBe('checkbox');
    expect(ouverture.checked).toBe(false);
    const penalite = champ<HTMLInputElement>(f, 'penalite_joker');
    expect(penalite.type).toBe('number');
    expect([penalite.min, penalite.max, penalite.value]).toEqual(['0', '50', '20']);
    const joueurs = champ<HTMLSelectElement>(f, 'nb_joueurs');
    expect(Array.from(joueurs.options).map((o) => o.value)).toEqual(['2', '3', '4', '5', '6']);
    expect(joueurs.value).toBe('3');
    expect(racine(f).textContent).not.toContain('Reprendre la partie');
  });

  it('« Commencer » envoie les valeurs choisies puis ouvre la partie avec ses étapes', async () => {
    const f = monter();
    const router = TestBed.inject(Router);
    const naviguer = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    const as = champ<HTMLSelectElement>(f, 'as');
    as.selectedIndex = 1;
    changer(as);
    const ouverture = champ<HTMLInputElement>(f, 'ouverture_suite_sans_joker');
    ouverture.checked = true;
    changer(ouverture);
    const penalite = champ<HTMLInputElement>(f, 'penalite_joker');
    penalite.value = '35';
    changer(penalite);
    const manches = champ<HTMLInputElement>(f, 'manches');
    manches.value = '99';
    changer(manches);
    const joueurs = champ<HTMLSelectElement>(f, 'nb_joueurs');
    joueurs.value = '5';
    changer(joueurs);
    f.detectChanges();
    expect(manches.value).toBe('10');

    commencer(f).click();
    const requete = http.expectOne('/api/parties/');
    expect(requete.request.method).toBe('POST');
    expect(requete.request.body).toEqual({
      jeu: jeuAvecOptions().code,
      nb_joueurs: 5,
      options: {
        as: 'toujours1',
        ouverture_suite_sans_joker: true,
        penalite_joker: 35,
        manches: 10,
      },
    });
    const partie = {
      id: 'p1',
      vue: vueFactice(),
      etapes: [{ message: 'Début', vue: vueFactice() }],
    };
    requete.flush(partie, { status: 201, statusText: 'Created' });
    expect(naviguer).toHaveBeenCalledWith(['/partie'], { state: { partie } });
  });

  it("n'envoie qu'un seul POST pour deux clics pendant la requête", () => {
    const f = monter([jeuSansOption()]);
    commencer(f).click();
    f.detectChanges();
    commencer(f).click();
    const requetes = http.match('/api/parties/');
    expect(requetes.length).toBe(1);
    expect(commencer(f).disabled).toBe(true);
    requetes[0].flush({ erreur: 'Non.' }, { status: 400, statusText: 'Bad Request' });
  });

  it('affiche un 400 sous le formulaire et permet de réessayer', () => {
    const f = monter([jeuSansOption()]);
    commencer(f).click();
    http
      .expectOne('/api/parties/')
      .flush(
        { erreur: 'Valeur invalide pour l’option.' },
        { status: 400, statusText: 'Bad Request' },
      );
    f.detectChanges();
    const erreur = racine(f).querySelector('[role="alert"]');
    expect(erreur?.textContent).toContain('Valeur invalide');
    expect(commencer(f).disabled).toBe(false);
  });

  it('propose « Reprendre la partie » quand une partie est en cours', () => {
    const f = monter([jeuAvecOptions()], { id: 'p1', vue: vueFactice() });
    const lien = Array.from(racine(f).querySelectorAll('a')).find(
      (a) => a.textContent?.trim() === 'Reprendre la partie',
    );
    expect(lien?.getAttribute('href')).toBe('/partie');
  });

  it('affiche le message reçu de la navigation', async () => {
    const harness = await RouterTestingHarness.create();
    await TestBed.inject(Router).navigate([''], {
      state: { message: 'Aucune partie en cours.' },
    });
    harness.detectChanges();
    repondre([jeuAvecOptions()]);
    harness.detectChanges();
    expect(harness.routeNativeElement?.textContent).toContain('Aucune partie en cours.');
  });
});
