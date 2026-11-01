import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { DescriptionJeu } from '../../core/vue';
import { jeuAvecOptions, jeuSansOption } from '../../../testing/jeux';
import { ReglesPage } from './regles.page';

let http: HttpTestingController;
const PREMIER = jeuAvecOptions().nom;
const SECOND = jeuSansOption().nom;

beforeEach(() => {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([{ path: 'regles', component: ReglesPage }]),
    ],
  });
  http = TestBed.inject(HttpTestingController);
});

afterEach(() => http.verify());

async function ouvrir(url: string, jeux: DescriptionJeu[] = [jeuAvecOptions(), jeuSansOption()]) {
  const harnais = await RouterTestingHarness.create();
  await harnais.navigateByUrl(url);
  http.expectOne('/api/jeux/').flush(jeux);
  harnais.detectChanges();
  return harnais;
}

const onglets = (h: RouterTestingHarness) =>
  Array.from(h.routeNativeElement!.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
const panneau = (h: RouterTestingHarness) =>
  h.routeNativeElement!.querySelector<HTMLElement>('[role="tabpanel"]')!;
const actif = (h: RouterTestingHarness) =>
  onglets(h)
    .find((o) => o.getAttribute('aria-selected') === 'true')
    ?.textContent?.trim();

describe('page des règles', () => {
  it('montre un onglet par jeu, le premier choisi par défaut', async () => {
    const h = await ouvrir('/regles');
    expect(onglets(h).map((o) => o.textContent?.trim())).toEqual([PREMIER, SECOND]);
    expect(actif(h)).toBe(PREMIER);
    const texte = panneau(h).textContent!;
    expect(texte).toContain('De 2 à 6 joueurs');
    expect(Array.from(panneau(h).querySelectorAll('h3')).map((t) => t.textContent)).toEqual([
      'Le jeu',
      'Un tour',
    ]);
    expect(panneau(h).querySelectorAll('li').length).toBe(3);
    expect(panneau(h).getAttribute('aria-labelledby')).toBe(onglets(h)[0].id);
  });

  it('ouvre l’onglet du jeu donné dans l’URL', async () => {
    const h = await ouvrir('/regles?jeu=factice');
    expect(actif(h)).toBe(SECOND);
    expect(panneau(h).textContent).toContain('3 joueurs');
    expect(panneau(h).textContent).toContain('Pas encore de rappel des règles pour ce jeu.');
  });

  it('un code inconnu montre le premier jeu', async () => {
    const h = await ouvrir('/regles?jeu=inconnu');
    expect(actif(h)).toBe(PREMIER);
  });

  it('un clic change d’onglet et l’URL', async () => {
    const h = await ouvrir('/regles');
    onglets(h)[1].click();
    await h.fixture.whenStable();
    h.detectChanges();
    expect(actif(h)).toBe(SECOND);
    expect(TestBed.inject(Router).url).toBe('/regles?jeu=factice');
  });

  it('les flèches passent d’un onglet à l’autre, en boucle', async () => {
    const h = await ouvrir('/regles');
    onglets(h)[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
    await h.fixture.whenStable();
    h.detectChanges();
    expect(actif(h)).toBe(SECOND);
    expect(onglets(h).map((o) => o.tabIndex)).toEqual([-1, 0]);
  });

  it('dit pourquoi les jeux ne sont pas chargés', async () => {
    const harnais = await RouterTestingHarness.create();
    await harnais.navigateByUrl('/regles');
    http
      .expectOne('/api/jeux/')
      .flush({ erreur: 'Panne.' }, { status: 500, statusText: 'Server Error' });
    harnais.detectChanges();
    expect(harnais.routeNativeElement!.querySelector('[role="alert"]')?.textContent).toContain(
      'Panne.',
    );
  });
});
