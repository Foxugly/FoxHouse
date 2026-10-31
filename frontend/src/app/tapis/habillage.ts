import { InjectionToken } from '@angular/core';
import { CarteVisible, Joker } from '../core/vue';

/** Un jeu de cartes : il dit seulement quelle image montrer pour une carte. */
export interface Habillage {
  nom: string;
  image(carte: CarteVisible | Joker): string;
}

const VALEURS: Record<string, string> = { A: 'ace', J: 'jack', Q: 'queen', K: 'king' };
const ENSEIGNES: Record<string, string> = {
  S: 'spades',
  H: 'hearts',
  D: 'diamonds',
  C: 'clubs',
};

const DOSSIER = '/cartes/webisso/';

export const HABILLAGE_WEBISSO: Habillage = {
  nom: 'webisso',
  image(carte) {
    if ('joker' in carte) {
      const numero = Number(carte.id.split('-')[1]);
      return `${DOSSIER}${numero % 2 === 1 ? 'black' : 'red'}_joker.svg`;
    }
    const valeur = VALEURS[carte.valeur] ?? carte.valeur;
    return `${DOSSIER}${valeur}_of_${ENSEIGNES[carte.enseigne]}.svg`;
  },
};

export const HABILLAGE = new InjectionToken<Habillage>('HABILLAGE', {
  providedIn: 'root',
  factory: () => HABILLAGE_WEBISSO,
});
