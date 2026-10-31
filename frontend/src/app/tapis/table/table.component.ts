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
  largeurCarte,
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
/** Les mains des autres sièges sont plus petites. */
const ECHELLE_AUTRES = 0.62;
/** Cartes des groupes et des zones du centre. */
const ECHELLE_GROUPE = 0.75;
const ECHELLE_CENTRE = 0.9;
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

/** Hauteur d'un siège hors cartes : marge de la carte soulevée, nom, compteurs, espaces. */
const HAUTEUR_HORS_CARTES = 16 + 44;
/** Espace laissé entre la main du joueur et le siège voisin. */
const MARGE_VOISIN = 8;
/** Largeur supposée du nom et des compteurs d'un siège. */
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
function lignesCompteursEnPlus(siege: Siege, largeur: number): number {
  let lignes = 1;
  let ligne = 0;
  for (const c of siege.compteurs) {
    const l = `${c.libelle} : ${c.valeur}`.length * CHASSE_COMPTEUR;
    if (ligne > 0 && ligne + ECART_COMPTEURS + l > largeur) {
      lignes++;
      ligne = l;
    } else {
      ligne += (ligne > 0 ? ECART_COMPTEURS : 0) + l;
    }
  }
  return lignes - 1;
}

/** Le rectangle qu'occupe un siège sur la table, estimé sans mesurer le rendu. */
function cadreSiege(place: PlaceSiege): Cadre {
  const largeur = Math.min(
    place.largeurMax,
    Math.max(LARGEUR_ETIQUETTES, ...place.zones.map((z) => z.largeur)),
  );
  const cartes = place.zones.map(({ zone, cw, largeur: dispo }) => {
    const { rangees } = pasCartes(zone.cartes.length, cw, dispo);
    return cw * (RAPPORT_CARTE + (rangees - 1) * 0.7);
  });
  const hauteur =
    HAUTEUR_HORS_CARTES +
    lignesCompteursEnPlus(place.siege, largeur) * LIGNE_COMPTEURS +
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
function demiHauteurSiege(cw: number, rangees: number): number {
  return (HAUTEUR_HORS_CARTES + cw * (RAPPORT_CARTE + (rangees - 1) * 0.7)) / 2;
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
): number {
  const n = positions.length;
  if (n < 2) return Infinity;
  const joueur = positions[0];
  // Majorant : la main du joueur sur deux rangées.
  const ecart = demiHauteurSiege(cw, 2) + demiHauteurSiege(cwAutres, 1);
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
 * pas minimal de `pasCartes`.
 */
function largeurMainUtile(nb: number, cw: number): number {
  return cw * (1 + 0.42 * Math.max(0, Math.ceil(nb / 2) - 1));
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
  cwAutres: number,
): void {
  const n = positions.length;
  const joueur = positions[0];
  const demiVoisin = demiHauteurSiege(cwAutres, 1);
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

@Component({
  selector: 'app-table',
  imports: [CarteComponent, MainComponent],
  templateUrl: './table.component.html',
  styleUrl: './table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TableComponent {
  readonly vue = input.required<VueTable>();
  readonly selection = input<Selection>({ cartes: [], cible: null });
  readonly basculer = output<string>();
  readonly choisirCible = output<string | null>();

  private readonly largeur = signal(LARGEUR_DEFAUT);
  private readonly hauteur = signal(HAUTEUR_DEFAUT);

  protected readonly cw = computed(() => largeurCarte(this.largeur(), this.hauteur()));
  protected readonly cwGroupe = computed(() => this.cw() * ECHELLE_GROUPE);
  protected readonly cwCentre = computed(() => this.cw() * ECHELLE_CENTRE);

  /** La main du joueur se sélectionne seulement si une action prend des cartes. */
  private readonly mainSelectionnable = computed(() =>
    this.vue().actions.some((a) => a.cartes_max > 0),
  );

  protected readonly places = computed<PlaceSiege[]>(() => {
    const { sieges, zones } = this.vue();
    const l = this.largeur();
    const h = this.hauteur();
    const cw = this.cw();
    const cwAutres = cw * ECHELLE_AUTRES;
    const n = sieges.length;
    // Le siège du joueur remonte vers le centre, et assez pour ne pas déborder sur le bord.
    const basJoueur = h - BORD_TABLE - demiHauteurSiege(cw, 2);
    const positions = positionsSieges(n, l, h).map((p, i) =>
      i === 0 ? { x: p.x, y: Math.min(basJoueur, h / 2 + (p.y - h / 2) * REMONTEE_JOUEUR) } : p,
    );
    const largeursMains = positions.map(({ x }) =>
      Math.max(cwAutres, Math.min(l / (n * 0.55), 150, 2 * Math.min(x, l - x))),
    );
    const largeurPleine = Math.min(0.7 * l, l - 40);
    const nbJoueur = zones.find((z) => z.siege === sieges[0]?.id && z.type === 'main')?.cartes
      .length;
    const libre = largeurEntreVoisins(positions, largeursMains, cw, cwAutres);
    if (libre >= Math.min(largeurPleine, largeurMainUtile(nbJoueur ?? 0, cw))) {
      largeursMains[0] = Math.max(cw, Math.min(largeurPleine, libre));
    } else {
      // Trop étroit entre les voisins : la main garde sa largeur, les voisins remontent.
      largeursMains[0] = Math.max(cw, largeurPleine);
      const { rangees } = pasCartes(nbJoueur ?? 0, cw, largeursMains[0]);
      remonterVoisins(
        positions,
        largeursMains,
        largeursMains[0],
        demiHauteurSiege(cw, rangees),
        cwAutres,
      );
    }
    return sieges.map((siege, i) => {
      const joueur = i === 0;
      const { x, y } = positions[i];
      const cwSiege = joueur ? cw : cwAutres;
      const largeurMain = largeursMains[i];
      return {
        siege,
        x,
        y,
        joueur,
        largeurMax: 2 * Math.min(x, l - x),
        zones: zones
          .filter((z) => z.siege === siege.id && z.type !== 'pli')
          .map((zone) => ({
            zone,
            cw: cwSiege,
            largeur:
              zone.type === 'main'
                ? largeurMain
                : Math.min(largeurMain, largeurRangee(zone.cartes.length, cwSiege, PAS_LIGNE)),
          })),
      };
    });
  });

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
      this.places().map(cadreSiege),
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
