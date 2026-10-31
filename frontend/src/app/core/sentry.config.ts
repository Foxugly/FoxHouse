/**
 * Configuration Sentry du frontend.
 *
 * Le DSN d'un SPA est PUBLIC (conçu pour vivre dans le code client) : sans risque
 * à committer. Vide, Sentry reste inactif et le build est valide. Pour l'activer,
 * coller ici le DSN du projet « foxhouse-frontend » (org foxugly-srl, de.sentry.io)
 * une fois le projet créé ; la CSP de nginx autorise déjà *.ingest.de.sentry.io.
 */
export const SENTRY_DSN = '';
export const SENTRY_ENV = 'production';

// Version déployée, pour corréler une erreur Sentry au commit. Remplacé au build
// CI (sed) par le SHA du commit ; vide en dev → pas de release taguée. Ne pas
// reformater cette ligne : la CI la cible littéralement.
export const SENTRY_RELEASE = '';
