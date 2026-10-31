/**
 * Descriptions de jeux pour les tests, telles que `GET /api/jeux/` les rend. Les specs des pages
 * passent par ici : elles n'ont pas à nommer le jeu dont viennent les données.
 */
import { DescriptionJeu } from '../app/core/vue';

/** Un jeu de 2 à 6 joueurs avec des options des trois types. */
export const jeuAvecOptions = (): DescriptionJeu => ({
  code: 'rami51',
  nom: 'Rami 51',
  min_joueurs: 2,
  max_joueurs: 6,
  options: [
    {
      code: 'as',
      libelle: "Valeur de l'as",
      type: 'choix',
      defaut: 'bas1_haut11',
      choix: [
        { valeur: 'bas1_haut11', libelle: '1 en bas de suite, 11 ailleurs' },
        { valeur: 'toujours1', libelle: 'Toujours 1' },
        { valeur: 'toujours11', libelle: 'Toujours 11' },
      ],
    },
    {
      code: 'ouverture_suite_sans_joker',
      libelle: 'Ouverture avec une suite sans joker',
      type: 'booleen',
      defaut: false,
    },
    {
      code: 'penalite_joker',
      libelle: 'Pénalité du joker',
      type: 'entier',
      defaut: 20,
      minimum: 0,
      maximum: 50,
    },
    {
      code: 'manches',
      libelle: 'Nombre de manches',
      type: 'entier',
      defaut: 5,
      minimum: 1,
      maximum: 10,
    },
  ],
});

/** Un jeu sans option, d'un nombre de joueurs fixe. */
export const jeuSansOption = (): DescriptionJeu => ({
  code: 'factice',
  nom: 'Jeu factice',
  min_joueurs: 3,
  max_joueurs: 3,
  options: [],
});
