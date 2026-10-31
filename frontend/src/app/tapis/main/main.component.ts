import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Carte } from '../../core/vue';
import { CarteComponent, RAPPORT_CARTE } from '../carte/carte.component';
import { indexRenforce, pasCartes } from '../disposition';
import { Selection } from '../selection';

/** Marge au-dessus de la main pour la place d'une carte soulevée. */
const MARGE_HAUT = 16;
/** Écart vertical entre deux rangées, en largeurs de carte. */
const ECART_RANGEES = 0.7;

@Component({
  selector: 'app-main',
  imports: [CarteComponent],
  templateUrl: './main.component.html',
  styleUrl: './main.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[style.width.px]': 'largeurDispo()',
    '[style.height.px]': 'hauteur()',
  },
})
export class MainComponent {
  readonly cartes = input.required<Carte[]>();
  readonly largeurDispo = input.required<number>();
  readonly cw = input.required<number>();
  readonly selectionnable = input(false);
  readonly selection = input<Selection>({ cartes: [], cible: null });
  readonly basculer = output<string>();

  private readonly disposition = computed(() =>
    pasCartes(this.cartes().length, this.cw(), this.largeurDispo()),
  );

  /** Plusieurs rangées : la main est serrée, l'index des cartes doit rester lisible. */
  protected readonly renforce = computed(() => {
    const { pas, rangees } = this.disposition();
    return rangees > 1 || indexRenforce(pas, this.cw());
  });

  protected readonly hauteur = computed(
    () =>
      MARGE_HAUT +
      this.cw() * RAPPORT_CARTE +
      (this.disposition().rangees - 1) * this.cw() * ECART_RANGEES,
  );

  protected readonly placees = computed(() => {
    const { pas, parRangee } = this.disposition();
    const cw = this.cw();
    const largeur = this.largeurDispo();
    const total = this.cartes().length;
    return this.cartes().map((carte, i) => {
      const rangee = Math.floor(i / parRangee);
      const colonne = i % parRangee;
      const nbRangee = Math.min(parRangee, total - rangee * parRangee);
      const decalage = Math.max(0, (largeur - cw - (nbRangee - 1) * pas) / 2);
      return {
        carte,
        id: 'id' in carte ? carte.id : null,
        // `pasCartes` garantit que la rangée tient : deux cartes ne partagent jamais un x.
        gauche: decalage + colonne * pas,
        haut: MARGE_HAUT + rangee * cw * ECART_RANGEES,
        z: i + 1,
      };
    });
  });

  protected estSelectionnee(id: string | null): boolean {
    return id !== null && this.selection().cartes.includes(id);
  }

  protected choisir(id: string | null): void {
    if (this.selectionnable() && id !== null) this.basculer.emit(id);
  }
}
