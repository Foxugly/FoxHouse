import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
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

@Component({
  selector: 'app-menu',
  templateUrl: './menu.component.html',
  styleUrl: './menu.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MenuComponent {
  readonly vue = input.required<VueTable>();
  readonly selection = input<Selection>({ cartes: [], cible: null });
  /** Une requête est en cours : aucune action ne part. */
  readonly occupe = input(false);
  readonly agir = output<Action>();

  protected activable(action: Action): boolean {
    return !this.occupe() && actionActivable(action, this.selection());
  }

  private readonly instance = ++instances;

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
