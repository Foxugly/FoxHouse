export interface Point {
  x: number;
  y: number;
}

export interface PasCartes {
  pas: number;
  rangees: number;
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

/**
 * Pas entre les cartes d'une main : 1,08·cw au plus, 0,42·cw au moins sur une rangée. Sinon, le
 * moins de rangées possible avec un pas d'au moins 0,8 × 0,42·cw : deux cartes d'une même rangée
 * ne sont jamais au même endroit, le coin de chacune reste visible, et la rangée tient dans
 * `largeurDispo` (dès qu'elle vaut au moins `cw`).
 */
export function pasCartes(nb: number, cw: number, largeurDispo: number): PasCartes {
  if (nb <= 1) return { pas: 0, rangees: 1, parRangee: nb };
  const pasMax = 1.08 * cw;
  const pasMin = 0.42 * cw;
  const libre = largeurDispo - cw;
  const pasUneRangee = Math.min(pasMax, libre / (nb - 1));
  if (pasUneRangee >= pasMin) return { pas: pasUneRangee, rangees: 1, parRangee: nb };
  for (let rangees = 2; rangees < nb; rangees++) {
    const parRangee = Math.ceil(nb / rangees);
    if (parRangee === 1) break;
    const pas = Math.min(pasMax, libre / (parRangee - 1));
    if (pas >= pasMin * 0.8) return { pas, rangees: Math.ceil(nb / parRangee), parRangee };
  }
  return { pas: 0, rangees: nb, parRangee: 1 };
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
 * milieu, raccourcie par les sièges du haut et du bas, rétrécie par ceux des côtés. Quand les
 * sièges y laissent trop peu de place (en largeur, ou moins de `hauteurMin` en hauteur), le centre
 * prend presque toute la largeur dans le plus grand espace vertical libre entre les sièges. Il
 * garde au moins `hauteurMin` (une rangée de cartes) : si aucun espace libre n'est assez haut, il
 * déborde sur les sièges, centré sur le plus grand espace et gardé dans la table.
 */
export function placerCentre(
  sieges: Cadre[],
  largeur: number,
  hauteur: number,
  hauteurMin = 0,
): Cadre {
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
  const largeOk = bande.droite - bande.gauche >= Math.max(LARGEUR_CENTRE_MIN, 0.4 * largeur);
  if (largeOk && bande.bas - bande.haut >= hauteurMin) return bande;

  const gauche = 0.1 * largeur;
  const droite = 0.9 * largeur;
  const obstacles = sieges
    .filter((s) => s.droite > gauche && s.gauche < droite)
    .sort((a, b) => a.haut - b.haut);
  let meilleur = { haut: hauteur / 2, bas: hauteur / 2 };
  const essayer = (haut: number, bas: number) => {
    if (bas - haut > meilleur.bas - meilleur.haut) meilleur = { haut, bas };
  };
  let curseur = 0.08 * hauteur;
  for (const o of obstacles) {
    essayer(curseur, o.haut - ECART_CENTRE);
    curseur = Math.max(curseur, o.bas + ECART_CENTRE);
  }
  essayer(curseur, 0.92 * hauteur);
  const plancher = Math.min(hauteurMin, hauteur);
  const manque = plancher - (meilleur.bas - meilleur.haut);
  if (manque > 0) {
    const haut = Math.max(0, Math.min(meilleur.haut - manque / 2, hauteur - plancher));
    meilleur = { haut, bas: haut + plancher };
  }
  return { gauche, droite, ...meilleur };
}
