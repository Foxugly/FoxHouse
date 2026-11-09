import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { VueTable } from '../../core/vue';

/**
 * Le panneau d'informations de la partie (manche, donneur, atout…), en lecture seule : les actions
 * sont dans la barre sous la table (`app-actions`).
 */
@Component({
  selector: 'app-menu',
  templateUrl: './menu.component.html',
  styleUrl: './menu.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MenuComponent {
  readonly vue = input.required<VueTable>();
}
