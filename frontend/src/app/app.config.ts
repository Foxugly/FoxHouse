import { ApplicationConfig, ErrorHandler, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withXsrfConfiguration } from '@angular/common/http';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { SentryErrorHandler } from './core/sentry';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Erreurs Angular non gérées → Sentry (si un DSN est configuré), puis la console.
    { provide: ErrorHandler, useClass: SentryErrorHandler },
    provideRouter(routes),
    // Django pose le cookie XSRF-TOKEN ; Angular le renvoie en X-XSRF-TOKEN sur les POST relatifs.
    provideHttpClient(
      withXsrfConfiguration({ cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN' }),
    ),
  ],
};
