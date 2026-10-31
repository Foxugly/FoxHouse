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
