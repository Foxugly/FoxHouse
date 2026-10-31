import { Location } from '@angular/common';
import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  Injector,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { ApiService, ErreurApi, PartieCreee, ResultatCoup } from '../../core/api.service';
import { Action, VueTable } from '../../core/vue';
import { MenuComponent } from '../../tapis/menu/menu.component';
import { basculer, choisirCible, Selection } from '../../tapis/selection';
import { TableComponent } from '../../tapis/table/table.component';
import { prendreEtatNavigation } from '../etat-navigation';
import { Relecture } from './relecture';

export const AUCUNE_PARTIE = 'Aucune partie en cours.';

const SELECTION_VIDE: Selection = { cartes: [], cible: null };

/** La partie passée par l'accueil après « Commencer », si l'état en contient une. */
function partieRecue(valeur: unknown): PartieCreee | null {
  const p = valeur as Partial<PartieCreee> | null | undefined;
  return typeof p?.id === 'string' && p.vue && Array.isArray(p.etapes) ? (p as PartieCreee) : null;
}

@Component({
  selector: 'app-partie-page',
  imports: [TableComponent, MenuComponent],
  templateUrl: './partie.page.html',
  styleUrl: './partie.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PartiePage {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  /** Une réponse arrivée après la sortie de la page ne navigue pas et ne relance rien. */
  private readonly destroyRef = inject(DestroyRef);
  private readonly hote = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly injector = inject(Injector);

  private id: string | null = null;
  /** La dernière vue reçue du serveur : sa version part avec chaque action. */
  protected readonly vue = signal<VueTable | null>(null);
  protected readonly selection = signal<Selection>(SELECTION_VIDE);
  /** Une action est partie et attend sa réponse. */
  protected readonly occupe = signal(false);
  protected readonly erreur = signal<string | null>(null);
  protected readonly confirmation = signal(false);
  protected readonly relecture = new Relecture();

  /** Pendant la relecture, la table montre l'étape ; ensuite, la vue finale. */
  protected readonly vueAffichee = computed(() => this.relecture.etape()?.vue ?? this.vue());
  protected readonly selectionAffichee = computed(() =>
    this.relecture.enCours() ? SELECTION_VIDE : this.selection(),
  );
  protected readonly bloque = computed(() => this.occupe() || this.relecture.enCours());

  constructor() {
    this.destroyRef.onDestroy(() => this.relecture.arreter());
    // Le bandeau disparaît à la fin de la relecture : s'il avait le focus (« Passer »), le focus
    // va à la première action possible plutôt que de retomber sur la page.
    let enCours = false;
    effect(() => {
      const maintenant = this.relecture.enCours();
      if (enCours && !maintenant && this.focusDans('.bandeau')) {
        this.focaliserApresRendu('app-menu button:not(:disabled)', '.panneau button');
      }
      enCours = maintenant;
    });
    const partie = partieRecue(prendreEtatNavigation(inject(Location), 'partie'));
    if (partie) {
      this.id = partie.id;
      this.vue.set(partie.vue);
      this.relecture.lancer(partie.etapes);
    } else {
      this.charger();
    }
  }

  private charger(): void {
    this.api
      .courante()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (partie) => {
          if (!partie) return this.quitterSansPartie();
          this.id = partie.id;
          this.vue.set(partie.vue);
        },
        error: (e: unknown) => {
          if (!(e instanceof ErreurApi)) throw e;
          if (e.statut === 404) return this.quitterSansPartie();
          this.erreur.set(e.message);
        },
      });
  }

  private quitterSansPartie(): void {
    void this.router.navigate([''], { state: { message: AUCUNE_PARTIE } });
  }

  protected agir(action: Action): void {
    const vue = this.vue();
    if (this.bloque() || !vue || !this.id) return;
    const { cartes, cible } = this.selection();
    this.occupe.set(true);
    this.erreur.set(null);
    this.api
      .agir(this.id, { version: vue.version, action: action.id, cartes, cible })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (r: ResultatCoup) => {
          this.apresReponse(r.vue);
          this.relecture.lancer(r.etapes);
        },
        error: (e: unknown) => {
          if (!(e instanceof ErreurApi)) {
            this.apresReponse(null);
            throw e;
          }
          if (e.statut === 404) return this.quitterSansPartie();
          this.apresReponse(e.vue ?? null);
          // 409 : la vue était périmée, la nouvelle suffit.
          if (e.statut !== 409) this.erreur.set(e.message);
        },
      });
  }

  private apresReponse(vue: VueTable | null): void {
    if (vue) this.vue.set(vue);
    this.selection.set(SELECTION_VIDE);
    this.occupe.set(false);
  }

  protected basculer(idCarte: string): void {
    if (this.relecture.enCours()) return;
    this.selection.update((s) => basculer(s, idCarte));
  }

  protected choisirCible(idGroupe: string | null): void {
    if (this.relecture.enCours()) return;
    this.selection.update((s) => choisirCible(s, idGroupe));
  }

  /** Un clic sur la table pendant la relecture saute à la vue finale. */
  protected passer(): void {
    this.relecture.passer();
  }

  /** Une partie terminée se quitte sans confirmation. */
  protected demanderNouvellePartie(): void {
    if (this.vue()?.terminee) return this.nouvellePartie();
    this.confirmation.set(true);
    this.focaliserApresRendu('.confirmation button.secondaire');
  }

  protected annulerNouvellePartie(): void {
    this.confirmation.set(false);
    this.focaliserApresRendu('button.nouvelle');
  }

  protected nouvellePartie(): void {
    void this.router.navigate(['']);
  }

  private focusDans(selecteur: string): boolean {
    const actif = this.hote.ownerDocument.activeElement;
    return !!actif && !!this.hote.querySelector(selecteur)?.contains(actif);
  }

  /** Après le prochain rendu, donne le focus au premier élément trouvé parmi les sélecteurs. */
  private focaliserApresRendu(...selecteurs: string[]): void {
    afterNextRender(
      () => {
        for (const s of selecteurs) {
          const el = this.hote.querySelector<HTMLElement>(s);
          if (el) return el.focus();
        }
      },
      { injector: this.injector },
    );
  }
}
