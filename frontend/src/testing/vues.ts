/**
 * Vues d'exemple typées pour les tests. Les specs du tapis passent par ici : elles n'ont pas à
 * nommer le jeu dont viennent les données.
 */
import { VueTable } from '../app/core/vue';
import debut from './vues/rami-debut.json';
import enAttente from './vues/rami-brouillon.json';
import finManche from './vues/rami-fin-manche.json';
import factice from './vues/factice.json';

/** Copie profonde : un test peut modifier sa vue sans toucher les autres. */
const copie = (donnees: unknown): VueTable => structuredClone(donnees) as VueTable;

/** Début de partie, 4 sièges, le joueur a la main. */
export const vueDebut = (): VueTable => copie(debut);
/** 4 sièges, un groupe provisoire au centre, des actions qui demandent des cartes. */
export const vueEnAttente = (): VueTable => copie(enAttente);
/** 3 sièges, des groupes au centre et un résultat. */
export const vueFinManche = (): VueTable => copie(finManche);
/** Le jeu factice du serveur. */
export const vueFactice = (): VueTable => copie(factice);
