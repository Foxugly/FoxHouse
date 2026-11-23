import { ErrorHandler, Injectable } from '@angular/core';
import * as Sentry from '@sentry/browser';

import { SENTRY_DSN, SENTRY_ENV, SENTRY_RELEASE } from './sentry.config';

/** Masque les paramètres d'URL sensibles (token, uid, code) en query string comme en fragment. */
export function scrubUrl(url: string): string {
  return url.replace(/([?&#](?:token|uid|code)=)[^&#]*/gi, '$1[Filtered]');
}

function scrubEvent<T extends Sentry.Event>(event: T): T {
  if (event.request?.url) {
    event.request.url = scrubUrl(event.request.url);
  }
  return event;
}

/** Initialise Sentry si un DSN est configuré (no-op sinon). Appelé dans main.ts. */
export function initSentry(): void {
  if (!SENTRY_DSN) {
    return;
  }
  // Ne pas initialiser Sentry en dev local (`ng serve` sur localhost) : les
  // artefacts du serveur de dev (rechargement de chunk HMR, backend de dev
  // indisponible) ne sont pas du signal de prod et seraient remontés tagués
  // `production` (SENTRY_ENV est figé à 'production' dans sentry.config).
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host === '[::1]') {
    return;
  }
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: SENTRY_ENV,
    release: SENTRY_RELEASE || undefined,
    // SDK 11 : `sendDefaultPii` a disparu au profit de `dataCollection`, dont
    // les défauts sont PLUS larges (IP/utilisateur, cookies, corps). On fixe
    // explicitement la base restrictive de la v10.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: {
        request: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
        response: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
      },
      httpBodies: [],
      urlQueryParams: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
      genAI: { inputs: false, outputs: false },
      databaseQueryData: false,
      queues: false,
      graphQL: { document: false, variables: false },
    },
    // SDK 11 diffuse les spans en flux par défaut, ce qui ignore
    // `beforeSendTransaction` (avertissement en console) : on garde le cycle
    // « static » de la v10 pour que le nettoyage ci-dessous s'applique.
    traceLifecycle: 'static',
    // Transitoire et bénin : un client gardant un onglet périmé après un
    // nouveau déploiement échoue à charger un lazy-chunk renommé. Non
    // actionnable — ne pas le remonter.
    ignoreErrors: [
      /Failed to fetch dynamically imported module/i,
      /error loading dynamically imported module/i,
    ],
    // Aucun jeton dans Sentry : URL de l'événement et breadcrumbs (navigation, xhr).
    beforeSend: (event) => scrubEvent(event),
    beforeSendTransaction: (event) => scrubEvent(event),
    beforeBreadcrumb: (crumb) => {
      const data = crumb.data as Record<string, unknown> | undefined;
      if (data) {
        for (const key of ['url', 'from', 'to']) {
          if (typeof data[key] === 'string') {
            data[key] = scrubUrl(data[key] as string);
          }
        }
      }
      return crumb;
    },
  });
}

/** Remonte les erreurs Angular non gérées à Sentry (si activé), et les loggue. */
@Injectable()
export class SentryErrorHandler implements ErrorHandler {
  handleError(error: unknown): void {
    if (SENTRY_DSN) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
    console.error(error);
  }
}
