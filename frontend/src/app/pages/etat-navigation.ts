import { Location } from '@angular/common';

/**
 * Lit une entrée de l'état de navigation (`router.navigate(…, { state })`) puis la retire de
 * l'historique : un rechargement de la page ne la retrouve pas. Le routeur a déjà écrit l'état
 * quand la page est construite.
 */
export function prendreEtatNavigation(location: Location, cle: string): unknown {
  const etat = location.getState();
  if (!etat || typeof etat !== 'object' || !(cle in etat)) return undefined;
  const { [cle]: valeur, ...reste } = etat as Record<string, unknown>;
  location.replaceState(location.path(true), '', reste);
  return valeur;
}
