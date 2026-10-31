/**
 * Configuration Sentry du frontend.
 *
 * Le DSN d'un SPA est PUBLIC (conçu pour vivre dans le code client). Laisser vide
 * pour désactiver Sentry ; le DSN du projet « foxhouse-frontend » arrive au plan 3.
 */
export const SENTRY_DSN = '';
export const SENTRY_ENV = 'production';

// Version déployée, pour corréler une erreur Sentry au commit. Remplacé au build
// CI (sed) par le SHA du commit ; vide en dev → pas de release taguée. Ne pas
// reformater cette ligne : la CI la cible littéralement.
export const SENTRY_RELEASE = '';
