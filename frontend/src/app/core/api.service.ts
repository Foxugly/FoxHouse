import { HttpClient, HttpErrorResponse, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';

import { Coup, DescriptionJeu, Etape, VueTable } from './vue';

export interface PartieCreee {
  id: string;
  vue: VueTable;
  etapes: Etape[];
}

export interface PartieCourante {
  id: string;
  vue: VueTable;
}

export interface ResultatCoup {
  vue: VueTable;
  etapes: Etape[];
}

/** Une erreur de l'API : `vue` accompagne un 409 (version périmée) ou un 400 (coup refusé). */
export class ErreurApi extends Error {
  constructor(
    readonly statut: number,
    message: string,
    readonly vue?: VueTable,
  ) {
    super(message);
    this.name = 'ErreurApi';
  }
}

const SANS_REPONSE = 'Le serveur ne répond pas.';

function enErreurApi(e: unknown): Observable<never> {
  if (!(e instanceof HttpErrorResponse)) {
    return throwError(() => e);
  }
  const corps = e.error;
  const message = typeof corps?.erreur === 'string' ? corps.erreur : SANS_REPONSE;
  return throwError(() => new ErreurApi(e.status, message, corps?.vue ?? undefined));
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  jeux(): Observable<DescriptionJeu[]> {
    return this.http.get<DescriptionJeu[]>('/api/jeux/').pipe(catchError(enErreurApi));
  }

  creer(jeu: string, nbJoueurs: number, options: Record<string, unknown>): Observable<PartieCreee> {
    return this.http
      .post<PartieCreee>('/api/parties/', { jeu, nb_joueurs: nbJoueurs, options })
      .pipe(catchError(enErreurApi));
  }

  /** La partie en cours du joueur, ou `null` (réponse 204). */
  courante(): Observable<PartieCourante | null> {
    return this.http
      .get<PartieCourante>('/api/parties/courante/', { observe: 'response' })
      .pipe(
        map((r: HttpResponse<PartieCourante>) => (r.status === 204 ? null : r.body)),
        catchError(enErreurApi),
      );
  }

  partie(id: string): Observable<PartieCourante> {
    return this.http.get<PartieCourante>(`/api/parties/${id}/`).pipe(catchError(enErreurApi));
  }

  agir(id: string, coup: Coup): Observable<ResultatCoup> {
    return this.http
      .post<ResultatCoup>(`/api/parties/${id}/actions/`, coup)
      .pipe(catchError(enErreurApi));
  }
}
