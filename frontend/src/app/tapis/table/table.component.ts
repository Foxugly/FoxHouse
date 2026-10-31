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
import { largeurCarte, positionsSieges } from '../disposition';
import { MainComponent } from '../main/main.component';
import { Selection } from '../selection';

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
    const n = sieges.length;
    const positions = positionsSieges(n, l, h);
    return sieges.map((siege, i) => {
      const joueur = i === 0;
      const x = positions[i].x;
      const y = joueur ? h / 2 + (positions[i].y - h / 2) * REMONTEE_JOUEUR : positions[i].y;
      const largeurMax = 2 * Math.min(x, l - x);
      const cwSiege = joueur ? cw : cw * ECHELLE_AUTRES;
      const largeurMain = Math.max(
        cwSiege,
        joueur ? Math.min(0.7 * l, l - 40) : Math.min(l / (n * 0.55), 150, largeurMax),
      );
      return {
        siege,
        x,
        y,
        joueur,
        largeurMax,
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

  protected readonly centre = computed(() => this.vue().zones.filter((z) => z.siege === null));

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
    const visible = zone.cartes.at(-1);
    if (visible) return visible;
    return zone.nombre === 0 ? null : { cachee: true };
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
