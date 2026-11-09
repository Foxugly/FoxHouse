/**
 * Configuration Sentry du frontend.
 *
 * Le DSN d'un SPA est PUBLIC (conçu pour vivre dans le code client) : sans risque
 * à committer. Vide, Sentry reste inactif et le build est valide. Ci-dessous : le
 * DSN du projet « foxhouse-frontend » (org foxugly-srl, de.sentry.io, 2026-11-09) ;
 * la CSP de nginx autorise *.ingest.de.sentry.io.
 */
export const SENTRY_DSN =
  'https://ee087fa72baa97e0845e8b821203c8e4@o4511389786701824.ingest.de.sentry.io/4512401361862736';
export const SENTRY_ENV = 'production';

// Version déployée, pour corréler une erreur Sentry au commit. Remplacé au build
// CI (sed) par le SHA du commit ; vide en dev → pas de release taguée. Ne pas
// reformater cette ligne : la CI la cible littéralement.
export const SENTRY_RELEASE = '';
