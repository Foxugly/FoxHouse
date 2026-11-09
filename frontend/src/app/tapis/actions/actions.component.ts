import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Action, VueTable } from '../../core/vue';
import { actionActivable, Selection } from '../selection';

/** Numéro des instances, pour des id uniques dans la page. */
let instances = 0;

/** Ce que l'action attend de la sélection, en clair : « 3 à 13 cartes », « 1 carte et un groupe ». */
export function contraintes(action: Action): string {
  const { cartes_min: min, cartes_max: max } = action;
  const pluriel = (n: number) => (n > 1 ? 'cartes' : 'carte');
  let cartes = '';
  if (max > 0) {
    if (min === max) cartes = `${min} ${pluriel(min)}`;
    else if (min === 0) cartes = `jusqu'à ${max} ${pluriel(max)}`;
    else cartes = `${min} à ${max} cartes`;
  }
  if (action.cible !== 'groupe') return cartes;
  return cartes ? `${cartes} et un groupe` : 'un groupe';
}

/**
 * La barre d'actions, sous la table : quand le jeu attend le joueur, elle le dit (« À toi de
 * jouer ») et montre un bouton par action ; sinon, elle dit qu'on attend les autres. Sa place reste
 * réservée, pour que la table ne change pas de taille d'un tour à l'autre.
 */
@Component({
  selector: 'app-actions',
  templateUrl: './actions.component.html',
  styleUrl: './actions.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class.a-toi]': 'aToi()' },
})
export class ActionsComponent {
  readonly vue = input.required<VueTable>();
  readonly selection = input<Selection>({ cartes: [], cible: null });
  /** Une requête est en cours ou des coups se rejouent : aucune action ne part. */
  readonly occupe = input(false);
  readonly agir = output<Action>();

  /** Le jeu attend un coup du joueur. */
  readonly aToi = computed(() => !this.occupe() && this.vue().actions.length > 0);

  private readonly instance = ++instances;

  protected activable(action: Action): boolean {
    return !this.occupe() && actionActivable(action, this.selection());
  }

  /**
   * Ce qui manque à la sélection pour une action désactivée, montré sous son bouton ; `null` si la
   * sélection convient (le bouton n'est alors désactivé que le temps d'une requête).
   */
  protected raisonDesactivee(action: Action): string | null {
    if (actionActivable(action, this.selection())) return null;
    return contraintes(action) || null;
  }

  protected idRaison(action: Action): string {
    return `raison-${this.instance}-${action.id}`;
  }
}
