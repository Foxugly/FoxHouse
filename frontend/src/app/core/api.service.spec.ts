import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiService, ErreurApi } from './api.service';
import { Coup, VueTable } from './vue';
import factice from '../../testing/vues/factice.json';

const vue = factice as unknown as VueTable;

describe('ApiService', () => {
  let api: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('courante rend null sur un 204', () => {
    let reponse: unknown = 'non reçu';
    api.courante().subscribe((r) => (reponse = r));
    http.expectOne('/api/parties/courante/').flush(null, { status: 204, statusText: 'No Content' });
    expect(reponse).toBeNull();
  });

  it('courante rend la partie sur un 200', () => {
    let reponse: unknown;
    api.courante().subscribe((r) => (reponse = r));
    http.expectOne('/api/parties/courante/').flush({ id: 'abc', vue });
    expect(reponse).toEqual({ id: 'abc', vue });
  });

  it('agir poste le corps exact', () => {
    const coup: Coup = { version: 3, action: 'retourner', cartes: ['c1'], cible: null };
    api.agir('abc', coup).subscribe();
    const requete = http.expectOne('/api/parties/abc/actions/');
    expect(requete.request.method).toBe('POST');
    expect(requete.request.body).toEqual(coup);
    requete.flush({ vue, etapes: [] });
  });

  it('creer poste le jeu, le nombre de joueurs et les options', () => {
    api.creer('factice', 3, { tours: 1 }).subscribe();
    const requete = http.expectOne('/api/parties/');
    expect(requete.request.body).toEqual({ jeu: 'factice', nb_joueurs: 3, options: { tours: 1 } });
    requete.flush({ id: 'abc', vue, etapes: [] }, { status: 201, statusText: 'Created' });
  });

  it('un 409 donne une ErreurApi portant la vue', () => {
    let erreur: unknown;
    api.agir('abc', { version: 1, action: 'x', cartes: [], cible: null }).subscribe({
      error: (e) => (erreur = e),
    });
    http
      .expectOne('/api/parties/abc/actions/')
      .flush({ erreur: 'Version périmée.', vue }, { status: 409, statusText: 'Conflict' });
    expect(erreur).toBeInstanceOf(ErreurApi);
    const e = erreur as ErreurApi;
    expect(e.statut).toBe(409);
    expect(e.message).toBe('Version périmée.');
    expect(e.vue).toEqual(vue);
  });

  it('une erreur réseau donne le message par défaut', () => {
    let erreur: unknown;
    api.jeux().subscribe({ error: (e) => (erreur = e) });
    http.expectOne('/api/jeux/').error(new ProgressEvent('error'));
    const e = erreur as ErreurApi;
    expect(e).toBeInstanceOf(ErreurApi);
    expect(e.statut).toBe(0);
    expect(e.message).toBe('Le serveur ne répond pas.');
    expect(e.vue).toBeUndefined();
  });

  it('une erreur 500 sans corps dit que le serveur a rencontré une erreur', () => {
    let erreur: unknown;
    api.jeux().subscribe({ error: (e) => (erreur = e) });
    http
      .expectOne('/api/jeux/')
      .flush('<h1>Server Error</h1>', { status: 500, statusText: 'Internal Server Error' });
    const e = erreur as ErreurApi;
    expect(e).toBeInstanceOf(ErreurApi);
    expect(e.statut).toBe(500);
    expect(e.message).toBe('Le serveur a rencontré une erreur.');
  });
});
