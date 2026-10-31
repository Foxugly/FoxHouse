/** Types de la vue d'une partie : ils reflètent exactement `backend/tapis/vue.py`. */

export interface CarteVisible {
  id: string;
  valeur: string;
  enseigne: string;
}

export interface Joker {
  id: string;
  joker: true;
  represente?: string | null;
}

export interface CarteCachee {
  cachee: true;
}

export type Carte = CarteVisible | Joker | CarteCachee;

export interface Compteur {
  libelle: string;
  valeur: string | number;
}

export interface Siege {
  id: number;
  nom: string;
  actif: boolean;
  compteurs: Compteur[];
}

export interface Groupe {
  id: string;
  provisoire: boolean;
  ciblable: boolean;
  cartes: Carte[];
}

export type TypeZone = 'main' | 'pile' | 'combinaisons' | 'pli' | 'annonces' | 'mises' | 'communes';

export interface Zone {
  id: string;
  type: TypeZone;
  siege: number | null;
  libelle: string;
  nombre: number | null;
  /** De la première posée à la dernière : la carte du dessus d'une pile est la dernière. */
  cartes: Carte[];
  groupes: Groupe[];
}

export interface LigneMenu {
  libelle: string;
  valeur: string | number | null;
}

export interface Action {
  id: string;
  libelle: string;
  cartes_min: number;
  cartes_max: number;
  cible: null | 'groupe';
}

export interface Resultat {
  titre: string;
  colonnes: string[];
  lignes: (string | number)[][];
}

export interface VueTable {
  schema: number;
  jeu: string;
  version: number;
  terminee: boolean;
  sieges: Siege[];
  zones: Zone[];
  menu: LigneMenu[];
  actions: Action[];
  resultat: Resultat | null;
}

/** Un pas de la partie, rejoué avant d'afficher la vue finale. */
export interface Etape {
  message: string;
  vue: VueTable;
}

export type TypeOption = 'booleen' | 'entier' | 'choix';

export interface DescriptionOption {
  code: string;
  libelle: string;
  type: TypeOption;
  defaut: boolean | number | string;
  choix?: { valeur: string | number; libelle: string }[];
  minimum?: number | null;
  maximum?: number | null;
}

export interface DescriptionJeu {
  code: string;
  nom: string;
  min_joueurs: number;
  max_joueurs: number;
  options: DescriptionOption[];
}

export interface Coup {
  version: number;
  action: string;
  cartes: string[];
  cible: string | null;
}
