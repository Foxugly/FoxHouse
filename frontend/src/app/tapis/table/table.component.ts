import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Carte, Groupe, Siege, VueTable, Zone } from '../../core/vue';
import { CarteComponent, RAPPORT_CARTE } from '../carte/carte.component';
import {
  Cadre,
  PART_VISIBLE_MIN,
  PAS_MIN,
  pasCartes,
  placerCentre,
  Point,
  positionsSieges,
} from '../disposition';
import { MainComponent } from '../main/main.component';
import { Selection } from '../selection';

/** Le dos montré pour une pile dont la carte du dessus est cachée. */
const DOS: Carte = { cachee: true };
/** Numéro des instances, pour des id uniques dans la page. */
let instances = 0;

/** Taille supposée tant que la table n'est pas mesurée (tests, premier rendu). */
const LARGEUR_DEFAUT = 800;
const HAUTEUR_DEFAUT = 560;
/** Le siège du joueur remonte un peu vers le centre pour que sa main reste sur le tapis. */
const REMONTEE_JOUEUR = 0.88;
/**
 * Toutes les cartes de la table ont la même largeur. Elle part de `CW_MAX_PART` du côté utile de
 * la table (au plus `CW_MAX`) et diminue tant que les sièges se chevauchent, sortent de la table ou
 * ne laissent pas de place au centre — donc selon l'écran, le nombre de joueurs et de cartes. Elle
 * ne descend pas sous `CW_MIN` (une carte doit rester facile à toucher).
 */
const CW_MAX_PART = 1 / 12;
const CW_MAX = 96;
const CW_MIN = 34;
/** Plancher des cartes des autres sièges, quand même `CW_MIN` ne tient pas. */
const CW_AUTRES_MIN = 20;
/**
 * À partir de cette largeur, les cartes se chevauchent jusqu'à ne montrer que `PART_VISIBLE_MIN`
 * de chacune (leur coin reste lisible) ; en dessous, `PAS_MIN`.
 */
const CW_CHEVAUCHEMENT = 48;
/** Les textes de la table grandissent avec les cartes : ×1 à `CW_TEXTE`, jusqu'à `TEXTE_MAX`. */
const CW_TEXTE = 50;
const TEXTE_MAX = 1.4;
/** Pas entre deux cartes d'un groupe : assez pour lire l'index, sur une seule rangée. */
const PAS_GROUPE = 0.45;
/** Pas entre deux cartes d'une zone générique : côte à côte. */
const PAS_LIGNE = 1.08;
/** Le pli d'un siège se pose sur le segment qui va du centre de la table au siège, à cette part. */
const PLI_VERS_SIEGE = 0.45;

interface ZoneSiege {
  zone: Zone;
  cw: number;
  largeur: number;
  /** Pas minimal entre ses cartes, en largeurs de carte. */
  pasMin: number;
}

interface PliSiege {
  zone: Zone;
  x: number;
  y: number;
}

interface PlaceSiege {
  siege: Siege;
  x: number;
  y: number;
  /** Le siège du joueur, en bas. */
  joueur: boolean;
  /** Largeur au-delà de laquelle le siège sortirait de la table. */
  largeurMax: number;
  zones: ZoneSiege[];
}

/** Largeur d'une rangée de `nb` cartes de largeur `cw` espacées de `pas`·cw. */
function largeurRangee(nb: number, cw: number, pas: number): number {
  return cw * (1 + pas * Math.max(0, nb - 1));
}

/**
 * Hauteur d'un siège hors cartes : marge de la carte soulevée (16), nom, compteurs et espaces (44
 * à la taille de texte 1, `texte` fois plus ensuite).
 */
function hauteurHorsCartes(texte: number): number {
  return 16 + 44 * texte;
}
/** Espace laissé entre la main du joueur et le siège voisin. */
const MARGE_VOISIN = 8;
/** Largeur supposée du nom et des compteurs d'un siège, à la taille de texte 1. */
const LARGEUR_ETIQUETTES = 100;
/** Marges verticales autour d'une rangée de cartes au centre : haut du cadre, bords de la zone. */
const MARGES_ZONE_CENTRE = 10 + 16 + 8;
/** Espace entre deux zones d'un même siège, marge de la carte soulevée comprise. */
const ECART_ZONES = 20;

/** Largeur d'un caractère des compteurs (0,68 rem, chasse fixe), écart et hauteur d'une ligne. */
const CHASSE_COMPTEUR = 6.6;
const ECART_COMPTEURS = 8;
const LIGNE_COMPTEURS = 14;
/** Épaisseur du bord en bois de la table, que le siège du joueur ne recouvre pas. */
const BORD_TABLE = 14;

/** Lignes en plus de la première quand les compteurs d'un siège passent à la ligne. */
function lignesCompteursEnPlus(siege: Siege, largeur: number, texte: number): number {
  let lignes = 1;
  let ligne = 0;
  for (const c of siege.compteurs) {
    const l = `${c.libelle} : ${c.valeur}`.length * CHASSE_COMPTEUR * texte;
    if (ligne > 0 && ligne + ECART_COMPTEURS * texte + l > largeur) {
      lignes++;
      ligne = l;
    } else {
      ligne += (ligne > 0 ? ECART_COMPTEURS * texte : 0) + l;
    }
  }
  return lignes - 1;
}

/** Le rectangle qu'occupe un siège sur la table, estimé sans mesurer le rendu. */
function cadreSiege(place: PlaceSiege, texte: number): Cadre {
  const largeur = Math.min(
    place.largeurMax,
    Math.max(LARGEUR_ETIQUETTES * texte, ...place.zones.map((z) => z.largeur)),
  );
  const cartes = place.zones.map(({ zone, cw, largeur: dispo, pasMin }) => {
    const { rangees } = pasCartes(zone.cartes.length, cw, dispo, pasMin);
    return cw * (RAPPORT_CARTE + (rangees - 1) * 0.7);
  });
  const hauteur =
    hauteurHorsCartes(texte) +
    lignesCompteursEnPlus(place.siege, largeur, texte) * LIGNE_COMPTEURS * texte +
    cartes.reduce((a, b) => a + b, 0) +
    Math.max(0, cartes.length - 1) * ECART_ZONES;
  return {
    gauche: place.x - largeur / 2,
    droite: place.x + largeur / 2,
    haut: place.y - hauteur / 2,
    bas: place.y + hauteur / 2,
  };
}

/** Demi-hauteur estimée d'un siège dont la main de largeur `cw` tient sur `rangees` rangées. */
function demiHauteurSiege(cw: number, rangees: number, texte: number): number {
  return (hauteurHorsCartes(texte) + cw * (RAPPORT_CARTE + (rangees - 1) * 0.7)) / 2;
}

/**
 * Largeur de main du joueur (siège 0) qui ne passe pas sous ses voisins : quand un voisin est à
 * la même hauteur, la main s'arrête avant son bloc. Sans voisin proche, pas de limite.
 */
function largeurEntreVoisins(
  positions: Point[],
  largeursMains: number[],
  cw: number,
  cwAutres: number,
  texte: number,
): number {
  const n = positions.length;
  if (n < 2) return Infinity;
  const joueur = positions[0];
  // Majorant : la main du joueur sur deux rangées.
  const ecart = demiHauteurSiege(cw, 2, texte) + demiHauteurSiege(cwAutres, 1, texte);
  let demiLargeur = Infinity;
  for (const i of new Set([1, n - 1])) {
    const voisin = positions[i];
    if (Math.abs(voisin.y - joueur.y) >= ecart) continue;
    const libre = Math.abs(voisin.x - joueur.x) - largeursMains[i] / 2 - MARGE_VOISIN;
    demiLargeur = Math.min(demiLargeur, libre);
  }
  return 2 * demiLargeur;
}

/**
 * Largeur sous laquelle la main du joueur n'est plus utilisable : ses cartes sur deux rangées au
 * pas minimal `pasMin` de `pasCartes`.
 */
function largeurMainUtile(nb: number, cw: number, pasMin: number): number {
  return cw * (1 + pasMin * Math.max(0, Math.ceil(nb / 2) - 1));
}

/**
 * Sur une table étroite, les voisins du joueur (sièges 1 et n−1) remontent au-dessus de sa main
 * plutôt que de la rétrécir. Ils ne remontent pas plus haut que le siège suivant ne le permet :
 * au-delà, la main du joueur passe devant eux.
 */
function remonterVoisins(
  positions: Point[],
  largeursMains: number[],
  largeurJoueur: number,
  demiHauteurJoueur: number,
  cw: number,
  texte: number,
): void {
  const n = positions.length;
  const joueur = positions[0];
  const demiVoisin = demiHauteurSiege(cw, 1, texte);
  for (const i of new Set([1, n - 1])) {
    if (i === 0) continue;
    const voisin = positions[i];
    const ecartX = Math.abs(voisin.x - joueur.x);
    if (ecartX >= largeurJoueur / 2 + largeursMains[i] / 2 + MARGE_VOISIN) continue;
    const cible = joueur.y - demiHauteurJoueur - demiVoisin - MARGE_VOISIN;
    const suivant = n > 3 ? positions[i === 1 ? 2 : n - 2] : null;
    const limite = Math.max(demiVoisin, suivant ? suivant.y + 2 * demiVoisin + MARGE_VOISIN : 0);
    positions[i] = { x: voisin.x, y: Math.min(voisin.y, Math.max(cible, limite)) };
  }
}

/** Facteur des textes de la table pour des cartes de largeur `cw`. */
function tailleTexte(cw: number): number {
  return Math.min(TEXTE_MAX, Math.max(1, cw / CW_TEXTE));
}

/** Pas minimal entre les cartes d'une main, en largeurs de carte, pour des cartes de largeur `cw`. */
function pasMinPour(cw: number): number {
  return cw >= CW_CHEVAUCHEMENT ? PART_VISIBLE_MIN : PAS_MIN;
}

/** Nombre de cartes de la main d'un siège (0 s'il n'en a pas). */
function cartesEnMain(zones: Zone[], siege: number): number {
  return zones.find((z) => z.siege === siege && z.type === 'main')?.cartes.length ?? 0;
}

/**
 * Les sièges et leurs zones sur une table `l` × `h` : les cartes du joueur de largeur `cw`, celles
 * des autres sièges de largeur `cwAutres` (la même, sauf en dernier recours sur un petit écran).
 */
function agencer(vue: VueTable, l: number, h: number, cw: number, cwAutres = cw): PlaceSiege[] {
  const { sieges, zones } = vue;
  const n = sieges.length;
  const texte = tailleTexte(cw);
  const pasMin = pasMinPour(cw);
  const largeurPleine = Math.min(0.7 * l, l - 40);
  const nbJoueur = sieges.length ? cartesEnMain(zones, sieges[0].id) : 0;
  // Le siège du joueur remonte vers le centre, et assez pour ne pas déborder sur le bord.
  const basJoueur = h - BORD_TABLE - demiHauteurSiege(cw, 2, texte);
  // Les sièges des côtés s'écartent du bord assez pour une main de deux rangées au pas minimal.
  const margeCote =
    largeurMainUtile(
      Math.max(0, ...sieges.slice(1).map((s) => cartesEnMain(zones, s.id))),
      cwAutres,
      pasMinPour(cwAutres),
    ) /
      2 +
    BORD_TABLE +
    MARGE_VOISIN;
  const positions = positionsSieges(n, l, h, margeCote).map((p, i) =>
    i === 0 ? { x: p.x, y: Math.min(basJoueur, h / 2 + (p.y - h / 2) * REMONTEE_JOUEUR) } : p,
  );
  // Largeur d'un siège qui reste sur le feutre, en deçà du bord en bois.
  const surLeFeutre = (x: number) => 2 * (Math.min(x, l - x) - BORD_TABLE - MARGE_VOISIN);
  // La main d'un autre siège prend la place d'une rangée de ses cartes, dans sa part de la table.
  const largeursMains = positions.map(({ x }, i) =>
    Math.max(
      cwAutres,
      Math.min(
        l / (n * 0.55),
        largeurRangee(cartesEnMain(zones, sieges[i].id), cwAutres, pasMinPour(cwAutres)),
        surLeFeutre(x),
      ),
    ),
  );
  const libre = largeurEntreVoisins(positions, largeursMains, cw, cwAutres, texte);
  if (libre >= Math.min(largeurPleine, largeurMainUtile(nbJoueur, cw, pasMin))) {
    largeursMains[0] = Math.max(cw, Math.min(largeurPleine, libre));
  } else {
    // Trop étroit entre les voisins : la main garde sa largeur, les voisins remontent.
    largeursMains[0] = Math.max(cw, largeurPleine);
    const { rangees } = pasCartes(nbJoueur, cw, largeursMains[0], pasMin);
    remonterVoisins(
      positions,
      largeursMains,
      largeursMains[0],
      demiHauteurSiege(cw, rangees, texte),
      cwAutres,
      texte,
    );
  }
  return sieges.map((siege, i) => {
    const { x, y } = positions[i];
    const largeurMain = largeursMains[i];
    const cwSiege = i === 0 ? cw : cwAutres;
    return {
      siege,
      x,
      y,
      joueur: i === 0,
      largeurMax: Math.max(cwSiege, surLeFeutre(x)),
      zones: zones
        .filter((z) => z.siege === siege.id && z.type !== 'pli')
        .map((zone) => ({
          zone,
          cw: cwSiege,
          pasMin: i === 0 ? pasMin : pasMinPour(cwAutres),
          largeur:
            zone.type === 'main'
              ? largeurMain
              : Math.min(largeurMain, largeurRangee(zone.cartes.length, cwSiege, PAS_LIGNE)),
        })),
    };
  });
}

function seChevauchent(a: Cadre, b: Cadre): boolean {
  return a.gauche < b.droite && b.gauche < a.droite && a.haut < b.bas && b.haut < a.bas;
}

/**
 * Les sièges tiennent : chacun dans la table, aucun sur un autre, et le centre trouve une place
 * d'au moins une rangée de cartes sans toucher un siège.
 */
function convient(places: PlaceSiege[], l: number, h: number, cw: number): boolean {
  const texte = tailleTexte(cw);
  const cadres = places.map((p) => cadreSiege(p, texte));
  const tolerance = 1;
  for (const c of cadres) {
    if (c.gauche < BORD_TABLE - tolerance || c.droite > l - BORD_TABLE + tolerance) return false;
    if (c.haut < -tolerance || c.bas > h + tolerance) return false;
  }
  for (let i = 0; i < cadres.length; i++) {
    for (let j = i + 1; j < cadres.length; j++) {
      if (seChevauchent(cadres[i], cadres[j])) return false;
    }
  }
  const centre = placerCentre(cadres, l, h, cw * RAPPORT_CARTE + MARGES_ZONE_CENTRE);
  return !cadres.some((c) => seChevauchent(c, centre));
}

@Component({
  selector: 'app-table',
  imports: [CarteComponent, MainComponent],
  templateUrl: './table.component.html',
  styleUrl: './table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[style.--echelle-texte]': 'texte()' },
})
export class TableComponent {
  readonly vue = input.required<VueTable>();
  readonly selection = input<Selection>({ cartes: [], cible: null });
  readonly basculer = output<string>();
  readonly choisirCible = output<string | null>();

  private readonly largeur = signal(LARGEUR_DEFAUT);
  private readonly hauteur = signal(HAUTEUR_DEFAUT);

  /**
   * La largeur commune à toutes les cartes de la table : la plus grande, entre `CW_MIN` et le plafond
   * de l'écran, pour laquelle les sièges tiennent (voir `agencer` et `convient`).
   */
  private readonly tailles = computed(() => {
    const vue = this.vue();
    const l = this.largeur();
    const h = this.hauteur();
    const plafond = Math.max(CW_MIN, Math.min(CW_MAX, Math.min(l, h * 1.4) * CW_MAX_PART));
    for (let cw = Math.floor(plafond); cw >= CW_MIN; cw--) {
      if (convient(agencer(vue, l, h, cw), l, h, cw)) return { cw, cwAutres: cw };
    }
    // Dernier recours (petit écran, beaucoup de joueurs) : les cartes du joueur gardent la taille
    // minimale, celles des autres sièges rétrécissent juste assez pour que tout tienne.
    for (let cwAutres = CW_MIN - 1; cwAutres > CW_AUTRES_MIN; cwAutres--) {
      if (convient(agencer(vue, l, h, CW_MIN, cwAutres), l, h, CW_MIN)) {
        return { cw: CW_MIN, cwAutres };
      }
    }
    return { cw: CW_MIN, cwAutres: CW_AUTRES_MIN };
  });
  protected readonly cw = computed(() => this.tailles().cw);
  protected readonly cwGroupe = this.cw;
  protected readonly cwCentre = this.cw;

  /** Facteur des textes de la table, qui grandissent avec les cartes. */
  protected readonly texte = computed(() => tailleTexte(this.cw()));

  /** La main du joueur se sélectionne seulement si une action prend des cartes. */
  private readonly mainSelectionnable = computed(() =>
    this.vue().actions.some((a) => a.cartes_max > 0),
  );

  protected readonly places = computed<PlaceSiege[]>(() =>
    agencer(this.vue(), this.largeur(), this.hauteur(), this.cw(), this.tailles().cwAutres),
  );

  /**
   * Les zones de type « pli » d'un siège (la carte qu'il vient de jouer) ne restent pas dans son
   * bloc : elles se posent entre lui et le centre, comme sur une vraie table. Un pli vide ne
   * montre rien.
   */
  protected readonly plis = computed<PliSiege[]>(() => {
    const cx = this.largeur() / 2;
    const cy = this.hauteur() / 2;
    const zones = this.vue().zones;
    return this.places().flatMap((p) =>
      zones
        .filter((z) => z.siege === p.siege.id && z.type === 'pli' && z.cartes.length)
        .map((zone) => ({
          zone,
          x: cx + (p.x - cx) * PLI_VERS_SIEGE,
          y: cy + (p.y - cy) * PLI_VERS_SIEGE,
        })),
    );
  });

  protected readonly rapportCarte = RAPPORT_CARTE;
  protected readonly idTitre = `titre-resultat-${++instances}`;

  protected readonly centre = computed(() => this.vue().zones.filter((z) => z.siege === null));

  /** Le cadre des zones du centre, à l'écart des sièges, haut d'une rangée de cartes au moins. */
  protected readonly cadreCentre = computed(() =>
    placerCentre(
      this.places().map((p) => cadreSiege(p, this.texte())),
      this.largeur(),
      this.hauteur(),
      this.cwCentre() * RAPPORT_CARTE + MARGES_ZONE_CENTRE,
    ),
  );

  constructor() {
    const hote = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
    const destroyRef = inject(DestroyRef);
    afterNextRender(() => {
      this.mesurer(hote.clientWidth, hote.clientHeight);
      if (typeof ResizeObserver === 'undefined') return;
      const observateur = new ResizeObserver(([entree]) =>
        this.mesurer(entree.contentRect.width, entree.contentRect.height),
      );
      observateur.observe(hote);
      destroyRef.onDestroy(() => observateur.disconnect());
    });
  }

  private mesurer(largeur: number, hauteur: number): void {
    if (largeur > 0 && hauteur > 0) {
      this.largeur.set(largeur);
      this.hauteur.set(hauteur);
    }
  }

  protected selectionnable(place: PlaceSiege, zone: Zone): boolean {
    return place.joueur && zone.type === 'main' && this.mainSelectionnable();
  }

  /** La carte du dessus d'une pile, un dos si elle est cachée, rien si la pile est vide. */
  protected dessus(zone: Zone): Carte | null {
    return zone.cartes.at(-1) ?? ((zone.nombre ?? 0) > 0 ? DOS : null);
  }

  protected largeurGroupe(groupe: Groupe): number {
    return largeurRangee(groupe.cartes.length, this.cwGroupe(), PAS_GROUPE);
  }

  protected largeurPli(zone: Zone): number {
    return largeurRangee(zone.cartes.length, this.cwGroupe(), PAS_GROUPE);
  }

  protected largeurLigne(zone: Zone): number {
    return Math.min(
      largeurRangee(zone.cartes.length, this.cwCentre(), PAS_LIGNE),
      0.5 * this.largeur(),
    );
  }

  protected ciblable(groupe: Groupe): boolean {
    return groupe.ciblable;
  }

  protected estCible(groupe: Groupe): boolean {
    return this.selection().cible === groupe.id;
  }

  protected cibler(groupe: Groupe): void {
    if (!this.ciblable(groupe)) return;
    this.choisirCible.emit(this.estCible(groupe) ? null : groupe.id);
  }
}
