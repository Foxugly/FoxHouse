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

interface ZoneSiege {
  zone: Zone;
  cw: number;
  largeur: number;
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
/** Espace entre deux zones d'un même siège, marge de la carte soulevée comprise. */
const ECART_ZONES = 20;

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
    cartes.reduce((a, b) => a + b, 0) +
    Math.max(0, cartes.length - 1) * ECART_ZONES;
  return {
    gauche: place.x - largeur / 2,
    droite: place.x + largeur / 2,
    haut: place.y - hauteur / 2,
    bas: place.y + hauteur / 2,
  };
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
  const demiHauteurJoueur = (HAUTEUR_HORS_CARTES + cw * (RAPPORT_CARTE + 0.7)) / 2;
  const demiHauteurVoisin = (HAUTEUR_HORS_CARTES + cwAutres * RAPPORT_CARTE) / 2;
  let demiLargeur = Infinity;
  for (const i of new Set([1, n - 1])) {
    const voisin = positions[i];
    if (Math.abs(voisin.y - joueur.y) >= demiHauteurJoueur + demiHauteurVoisin) continue;
    const libre = Math.abs(voisin.x - joueur.x) - largeursMains[i] / 2 - MARGE_VOISIN;
    demiLargeur = Math.min(demiLargeur, libre);
  }
  return 2 * demiLargeur;
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
    const positions = positionsSieges(n, l, h).map((p, i) =>
      i === 0 ? { x: p.x, y: h / 2 + (p.y - h / 2) * REMONTEE_JOUEUR } : p,
    );
    const largeursMains = positions.map(({ x }) =>
      Math.max(cwAutres, Math.min(l / (n * 0.55), 150, 2 * Math.min(x, l - x))),
    );
    largeursMains[0] = Math.max(
      cw,
      Math.min(0.7 * l, l - 40, largeurEntreVoisins(positions, largeursMains, cw, cwAutres)),
    );
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
          .filter((z) => z.siege === siege.id)
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

  protected readonly rapportCarte = RAPPORT_CARTE;
  protected readonly idTitre = `titre-resultat-${++instances}`;

  protected readonly centre = computed(() => this.vue().zones.filter((z) => z.siege === null));

  /** Le cadre des zones du centre, à l'écart des sièges. */
  protected readonly cadreCentre = computed(() =>
    placerCentre(this.places().map(cadreSiege), this.largeur(), this.hauteur()),
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

  protected largeurLigne(zone: Zone): number {
    return Math.min(
      largeurRangee(zone.cartes.length, this.cwCentre(), PAS_LIGNE),
      0.5 * this.largeur(),
    );
  }

  protected ciblable(groupe: Groupe): boolean {
    return groupe.ciblable && !groupe.provisoire;
  }

  protected estCible(groupe: Groupe): boolean {
    return this.selection().cible === groupe.id;
  }

  protected cibler(groupe: Groupe): void {
    if (!this.ciblable(groupe)) return;
    this.choisirCible.emit(this.estCible(groupe) ? null : groupe.id);
  }
}
