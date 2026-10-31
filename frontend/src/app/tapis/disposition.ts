export interface Point {
  x: number;
  y: number;
}

export interface PasCartes {
  pas: number;
  rangees: 1 | 2;
  parRangee: number;
}

/**
 * Sièges répartis à intervalles égaux sur une ellipse. Écran : y vers le bas ; le siège 0 est en
 * bas au centre, les suivants vont vers la gauche, le haut puis la droite (sens horaire).
 */
export function positionsSieges(n: number, largeur: number, hauteur: number): Point[] {
  const rx = largeur / 2 - Math.max(40, 0.08 * largeur);
  const ry = hauteur / 2 - Math.max(40, 0.12 * hauteur);
  return Array.from({ length: n }, (_, i) => {
    const angle = Math.PI / 2 + (i * 2 * Math.PI) / n;
    return { x: largeur / 2 + rx * Math.cos(angle), y: hauteur / 2 + ry * Math.sin(angle) };
  });
}

export function largeurCarte(largeur: number, hauteur: number): number {
  return Math.max(34, Math.min(62, Math.min(largeur, hauteur * 1.4) / 15));
}

/** Pas entre les cartes d'une main : 1,08·cw au plus, 0,42·cw au moins, sinon deux rangées. */
export function pasCartes(nb: number, cw: number, largeurDispo: number): PasCartes {
  if (nb <= 1) return { pas: 0, rangees: 1, parRangee: nb };
  const pasMax = 1.08 * cw;
  const pasMin = 0.42 * cw;
  const pasUneRangee = Math.min(pasMax, (largeurDispo - cw) / (nb - 1));
  if (pasUneRangee >= pasMin) return { pas: pasUneRangee, rangees: 1, parRangee: nb };
  const parRangee = Math.ceil(nb / 2);
  const pas = Math.max(pasMin * 0.8, Math.min(pasMax, (largeurDispo - cw) / (parRangee - 1)));
  return { pas, rangees: 2, parRangee };
}

/** Les cartes très chevauchées affichent un index lisible par-dessus. */
export function indexRenforce(pas: number, cw: number): boolean {
  return pas < 0.6 * cw;
}

/** Un rectangle dans le repère de la table. */
export interface Cadre {
  gauche: number;
  droite: number;
  haut: number;
  bas: number;
}

/** Écart gardé entre les zones du centre et un siège. */
const ECART_CENTRE = 8;
/** En dessous de cette largeur, les zones du centre passent sous les sièges des côtés. */
const LARGEUR_CENTRE_MIN = 160;

/**
 * Le cadre des zones du centre, qui ne touche aucun siège. Sur une table large, c'est la bande du
 * milieu, raccourcie par les sièges du haut et du bas, rétrécie par ceux des côtés. Sur une table étroite, où les sièges des côtés
 * laisseraient trop peu de place, le centre prend presque toute la largeur dans le plus grand
 * espace vertical libre entre les sièges.
 */
export function placerCentre(sieges: Cadre[], largeur: number, hauteur: number): Cadre {
  const bande: Cadre = {
    gauche: 0.22 * largeur,
    droite: 0.78 * largeur,
    haut: 0.12 * hauteur,
    bas: 0.88 * hauteur,
  };
  const milieu = largeur / 2;
  for (const s of sieges) {
    if (s.bas <= bande.haut || s.haut >= bande.bas) continue;
    if (s.gauche < milieu && s.droite > milieu) {
      // Un siège au milieu, en haut ou en bas, raccourcit la bande.
      if (s.haut < hauteur / 2) bande.haut = Math.max(bande.haut, s.bas + ECART_CENTRE);
      else bande.bas = Math.min(bande.bas, s.haut - ECART_CENTRE);
    } else if (s.droite <= milieu) {
      bande.gauche = Math.max(bande.gauche, s.droite + ECART_CENTRE);
    } else {
      bande.droite = Math.min(bande.droite, s.gauche - ECART_CENTRE);
    }
  }
  if (bande.droite - bande.gauche >= Math.max(LARGEUR_CENTRE_MIN, 0.4 * largeur)) return bande;

  const gauche = 0.1 * largeur;
  const droite = 0.9 * largeur;
  const obstacles = sieges
    .filter((s) => s.droite > gauche && s.gauche < droite)
    .sort((a, b) => a.haut - b.haut);
  let meilleur = { haut: 0, bas: 0 };
  const essayer = (haut: number, bas: number) => {
    if (bas - haut > meilleur.bas - meilleur.haut) meilleur = { haut, bas };
  };
  let curseur = 0.08 * hauteur;
  for (const o of obstacles) {
    essayer(curseur, o.haut - ECART_CENTRE);
    curseur = Math.max(curseur, o.bas + ECART_CENTRE);
  }
  essayer(curseur, 0.92 * hauteur);
  return { gauche, droite, ...meilleur };
}
