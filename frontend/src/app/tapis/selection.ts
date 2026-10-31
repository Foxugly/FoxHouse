import { Action } from '../core/vue';

export interface Selection {
  cartes: string[];
  cible: string | null;
}

/** Ajoute la carte à la sélection, ou l'en retire si elle y est déjà. */
export function basculer(selection: Selection, idCarte: string): Selection {
  const cartes = selection.cartes.includes(idCarte)
    ? selection.cartes.filter((id) => id !== idCarte)
    : [...selection.cartes, idCarte];
  return { ...selection, cartes };
}

export function choisirCible(selection: Selection, idGroupe: string | null): Selection {
  return { ...selection, cible: idGroupe };
}

export function actionActivable(action: Action, selection: Selection): boolean {
  const nb = selection.cartes.length;
  if (nb < action.cartes_min || nb > action.cartes_max) return false;
  return action.cible !== 'groupe' || selection.cible !== null;
}
