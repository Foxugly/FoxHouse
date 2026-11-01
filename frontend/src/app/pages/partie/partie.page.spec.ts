import { Component } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PartieCreee } from '../../core/api.service';
import { Etape, VueTable } from '../../core/vue';
import { vueDebut, vueEnAttente, vueFactice } from '../../../testing/vues';
import { PartiePage } from './partie.page';
import { DELAI_ETAPE } from './relecture';

@Component({ template: '' })
class PageVide {}

let http: HttpTestingController;
let harness: RouterTestingHarness;

beforeEach(async () => {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([
        { path: '', component: PageVide },
        { path: 'partie', component: PartiePage },
      ]),
    ],
  });
  http = TestBed.inject(HttpTestingController);
  harness = await RouterTestingHarness.create();
});

afterEach(() => {
  http.verify();
  vi.useRealTimers();
});

const racine = () => harness.routeNativeElement as HTMLElement;
const texte = () => racine().textContent ?? '';
const boutons = () => Array.from(racine().querySelectorAll<HTMLButtonElement>('button'));
const bouton = (libelle: string) => boutons().find((b) => b.textContent?.trim() === libelle);
const bandeau = () => racine().querySelector('.bandeau');
const cartesDuJoueur = () =>
  Array.from(
    racine().querySelectorAll<HTMLElement>('.siege[data-siege="0"] .place[role="button"]'),
  );

/** Une vue de test reconnaissable à son menu. */
function vueMarquee(base: VueTable, marque: string, version = base.version): VueTable {
  return { ...base, version, menu: [{ libelle: 'Marque', valeur: marque }] };
}

/** Ouvre la page en direct (rechargement) : elle demande la partie courante. */
async function ouvrirEnDirect(vue: VueTable): Promise<void> {
  await harness.navigateByUrl('/partie');
  http.expectOne('/api/parties/courante/').flush({ id: 'p1', vue });
  harness.detectChanges();
}

/** Ouvre la page comme après « Commencer » : la partie et ses étapes passent par l'état. */
async function ouvrirApresCreation(partie: PartieCreee): Promise<void> {
  await TestBed.inject(Router).navigate(['/partie'], { state: { partie } });
  harness.detectChanges();
}

function troisEtapes(): Etape[] {
  return [1, 2, 3].map((i) => ({ message: `Étape ${i}`, vue: vueMarquee(vueFactice(), `e${i}`) }));
}

const creee = (): PartieCreee => ({
  id: 'p1',
  vue: vueMarquee(vueFactice(), 'finale'),
  etapes: troisEtapes(),
});

describe('PartiePage', () => {
  it('au chargement direct, montre la vue courante sans relecture', async () => {
    await ouvrirEnDirect(vueMarquee(vueFactice(), 'finale'));
    expect(texte()).toContain('finale');
    expect(bandeau()).toBeNull();
    expect(bouton('Retourner')?.disabled).toBe(false);
    expect(racine().querySelector('app-table')).not.toBeNull();
  });

  it("un 204 renvoie à l'accueil avec « Aucune partie en cours. »", async () => {
    const naviguer = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    await harness.navigateByUrl('/partie');
    http.expectOne('/api/parties/courante/').flush(null, { status: 204, statusText: 'No Content' });
    expect(naviguer).toHaveBeenCalledWith([''], {
      state: { message: 'Aucune partie en cours.' },
    });
  });

  it("un 404 renvoie aussi à l'accueil", async () => {
    const naviguer = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    await harness.navigateByUrl('/partie');
    http
      .expectOne('/api/parties/courante/')
      .flush({ erreur: 'Introuvable.' }, { status: 404, statusText: 'Not Found' });
    expect(naviguer).toHaveBeenCalledWith([''], {
      state: { message: 'Aucune partie en cours.' },
    });
  });

  it('rejoue les étapes reçues à la création, une toutes les 700 ms', async () => {
    vi.useFakeTimers();
    await ouvrirApresCreation(creee());
    expect(bandeau()?.textContent).toContain('Étape 1');
    expect(texte()).toContain('e1');
    expect(bouton('Retourner')?.disabled).toBe(true);
    vi.advanceTimersByTime(DELAI_ETAPE);
    harness.detectChanges();
    expect(bandeau()?.textContent).toContain('Étape 2');
    expect(texte()).toContain('e2');
    vi.advanceTimersByTime(2 * DELAI_ETAPE);
    harness.detectChanges();
    expect(bandeau()).toBeNull();
    expect(texte()).toContain('finale');
    expect(bouton('Retourner')?.disabled).toBe(false);
  });

  it('« Passer » affiche la vue finale et débloque les actions', async () => {
    vi.useFakeTimers();
    await ouvrirApresCreation(creee());
    bouton('Passer')!.click();
    harness.detectChanges();
    expect(bandeau()).toBeNull();
    expect(texte()).toContain('finale');
    expect(bouton('Retourner')?.disabled).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('un clic sur la table pendant la relecture saute à la vue finale', async () => {
    vi.useFakeTimers();
    await ouvrirApresCreation(creee());
    racine().querySelector<HTMLElement>('app-table')!.click();
    harness.detectChanges();
    expect(bandeau()).toBeNull();
    expect(texte()).toContain('finale');
  });

  it("agir envoie la version, l'action et la sélection, puis vide la sélection", async () => {
    const vue = vueEnAttente();
    const uneCarte = vue.actions.find((a) => a.cartes_min === 1 && a.cartes_max === 1)!;
    const idCarte = (vue.zones.find((z) => z.siege === 0)!.cartes[0] as { id: string }).id;
    await ouvrirEnDirect(vue);
    cartesDuJoueur()[0].click();
    harness.detectChanges();
    expect(bouton(uneCarte.libelle)?.disabled).toBe(false);

    bouton(uneCarte.libelle)!.click();
    harness.detectChanges();
    const requete = http.expectOne('/api/parties/p1/actions/');
    expect(requete.request.body).toEqual({
      version: vue.version,
      action: uneCarte.id,
      cartes: [idCarte],
      cible: null,
    });
    requete.flush({ vue: vueMarquee(vueEnAttente(), 'après', vue.version + 1), etapes: [] });
    harness.detectChanges();
    expect(texte()).toContain('après');
    expect(cartesDuJoueur()[0].getAttribute('aria-pressed')).toBe('false');
    expect(bouton(uneCarte.libelle)?.disabled).toBe(true);
  });

  it("le clic sur une carte joue l'action directe, sans bouton", async () => {
    const base = vueEnAttente();
    const uneCarte = base.actions.find((a) => a.cartes_min === 1 && a.cartes_max === 1)!;
    const vue = { ...base, actions: [{ ...uneCarte, direct: true }] };
    const idCarte = (vue.zones.find((z) => z.siege === 0)!.cartes[1] as { id: string }).id;
    await ouvrirEnDirect(vue);
    expect(bouton(uneCarte.libelle)).toBeUndefined();

    cartesDuJoueur()[1].click();
    cartesDuJoueur()[0].click();
    harness.detectChanges();
    const requete = http.expectOne('/api/parties/p1/actions/');
    expect(requete.request.body).toEqual({
      version: vue.version,
      action: uneCarte.id,
      cartes: [idCarte],
      cible: null,
    });
    requete.flush({ vue: vueMarquee(base, 'après', vue.version + 1), etapes: [] });
    harness.detectChanges();
    expect(texte()).toContain('après');
  });

  it("n'envoie qu'un seul POST pour deux clics pendant la requête", async () => {
    await ouvrirEnDirect(vueFactice());
    bouton('Retourner')!.click();
    harness.detectChanges();
    bouton('Retourner')!.click();
    const requetes = http.match('/api/parties/p1/actions/');
    expect(requetes.length).toBe(1);
    requetes[0].flush({ vue: vueFactice(), etapes: [] });
  });

  it('rejoue les étapes de la réponse, puis envoie la version de la vue finale', async () => {
    vi.useFakeTimers();
    await ouvrirEnDirect(vueFactice());
    bouton('Retourner')!.click();
    http
      .expectOne('/api/parties/p1/actions/')
      .flush({ vue: vueMarquee(vueFactice(), 'finale', 7), etapes: troisEtapes() });
    harness.detectChanges();
    expect(bandeau()?.textContent).toContain('Étape 1');
    bouton('Passer')!.click();
    harness.detectChanges();
    bouton('Retourner')!.click();
    const requete = http.expectOne('/api/parties/p1/actions/');
    expect(requete.request.body.version).toBe(7);
    requete.flush({ vue: vueFactice(), etapes: [] });
  });

  it('un 409 remplace la vue sans afficher de message', async () => {
    await ouvrirEnDirect(vueFactice());
    bouton('Retourner')!.click();
    http
      .expectOne('/api/parties/p1/actions/')
      .flush(
        { erreur: 'Version périmée.', vue: vueMarquee(vueFactice(), 'fraîche', 4) },
        { status: 409, statusText: 'Conflict' },
      );
    harness.detectChanges();
    expect(texte()).toContain('fraîche');
    expect(texte()).not.toContain('Version périmée.');
    expect(racine().querySelector('[role="alert"]')).toBeNull();
    expect(bouton('Retourner')?.disabled).toBe(false);
  });

  it('un 400 affiche le message et la vue reçue ; le message se ferme à la main', async () => {
    await ouvrirEnDirect(vueFactice());
    bouton('Retourner')!.click();
    http
      .expectOne('/api/parties/p1/actions/')
      .flush(
        { erreur: "Ce n'est pas ton tour.", vue: vueMarquee(vueFactice(), 'serveur') },
        { status: 400, statusText: 'Bad Request' },
      );
    harness.detectChanges();
    const alerte = racine().querySelector('[role="alert"]');
    expect(alerte?.textContent).toContain("Ce n'est pas ton tour.");
    expect(texte()).toContain('serveur');
    expect(bouton('Retourner')?.disabled).toBe(false);
    racine().querySelector<HTMLButtonElement>('[role="alert"] button')!.click();
    harness.detectChanges();
    expect(racine().querySelector('[role="alert"]')).toBeNull();
  });

  it("« Nouvelle partie » demande confirmation dans la page puis revient à l'accueil", async () => {
    await ouvrirEnDirect(vueDebut());
    const naviguer = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    bouton('Nouvelle partie')!.click();
    harness.detectChanges();
    expect(naviguer).not.toHaveBeenCalled();
    bouton('Continuer la partie')!.click();
    harness.detectChanges();
    expect(bouton('Continuer la partie')).toBeUndefined();
    bouton('Nouvelle partie')!.click();
    harness.detectChanges();
    bouton('Quitter la partie')!.click();
    expect(naviguer).toHaveBeenCalledWith(['']);
  });
  it('« Continuer la partie » rend le focus au bouton « Nouvelle partie »', async () => {
    await ouvrirEnDirect(vueDebut());
    bouton('Nouvelle partie')!.click();
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(document.activeElement).toBe(bouton('Continuer la partie'));
    bouton('Continuer la partie')!.click();
    harness.detectChanges();
    await harness.fixture.whenStable();
    expect(document.activeElement).toBe(bouton('Nouvelle partie'));
  });

  it('une partie terminée se quitte sans confirmation', async () => {
    await ouvrirEnDirect({ ...vueFactice(), terminee: true, actions: [] });
    const naviguer = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    bouton('Nouvelle partie')!.click();
    expect(naviguer).toHaveBeenCalledWith(['']);
    expect(bouton('Quitter la partie')).toBeUndefined();
  });

  it('quand « Passer » disparaît avec le focus, le focus va à la première action', async () => {
    vi.useFakeTimers();
    await ouvrirApresCreation(creee());
    const passer = bouton('Passer')!;
    passer.focus();
    expect(document.activeElement).toBe(passer);
    passer.click();
    harness.detectChanges();
    expect(document.activeElement).toBe(bouton('Retourner'));
  });

  it('à la fin naturelle de la relecture, le focus quitte aussi le bandeau', async () => {
    vi.useFakeTimers();
    await ouvrirApresCreation(creee());
    bouton('Passer')!.focus();
    vi.advanceTimersByTime(3 * DELAI_ETAPE);
    harness.detectChanges();
    expect(bandeau()).toBeNull();
    expect(document.activeElement).toBe(bouton('Retourner'));
  });

  it('une réponse arrivée après avoir quitté la page est abandonnée', async () => {
    await ouvrirEnDirect(vueFactice());
    bouton('Retourner')!.click();
    const requete = http.expectOne('/api/parties/p1/actions/');
    await harness.navigateByUrl('/');
    expect(requete.cancelled).toBe(true);
  });

  it('une partie courante arrivée après avoir quitté la page ne navigue pas', async () => {
    await harness.navigateByUrl('/partie');
    const requete = http.expectOne('/api/parties/courante/');
    await harness.navigateByUrl('/');
    expect(requete.cancelled).toBe(true);
  });
});
