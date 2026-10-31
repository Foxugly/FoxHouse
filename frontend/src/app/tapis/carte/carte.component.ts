import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { Carte } from '../../core/vue';
import { HABILLAGE } from '../habillage';

/** Rapport hauteur / largeur des images (167,09 × 242,67) ; le dos en CSS le reprend. */
export const RAPPORT_CARTE = 242.6669922 / 167.0869141;

const VALEURS_FR: Record<string, string> = { A: 'as', J: 'valet', Q: 'dame', K: 'roi' };
const ENSEIGNES_FR: Record<string, string> = {
  S: 'pique',
  H: 'cœur',
  D: 'carreau',
  C: 'trèfle',
};
const SYMBOLES: Record<string, string> = { S: '♠', H: '♥', D: '♦', C: '♣', '*': '*' };
const VALEURS_COURTES: Record<string, string> = { J: 'V', Q: 'D', K: 'R' };

const valeurCourte = (valeur: string) => VALEURS_COURTES[valeur] ?? valeur;
const symbole = (enseigne: string) => SYMBOLES[enseigne] ?? enseigne;

/** « 7C » → « 7♣ », « K* » → « R* » (couleur libre). */
export function libelleCourt(valeur: string, enseigne: string): string {
  return `${valeurCourte(valeur)}${symbole(enseigne)}`;
}

@Component({
  selector: 'app-carte',
  templateUrl: './carte.component.html',
  styleUrl: './carte.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[style.width.px]': 'largeur()',
    '[style.height.px]': 'hauteur()',
    '[class.selectionnee]': 'selectionnee()',
    '[class.provisoire]': 'provisoire()',
  },
})
export class CarteComponent {
  readonly carte = input.required<Carte>();
  readonly largeur = input(48);
  readonly indexRenforce = input(false);
  readonly selectionnee = input(false);
  readonly provisoire = input(false);

  private readonly habillage = inject(HABILLAGE);

  protected readonly hauteur = computed(() => this.largeur() * RAPPORT_CARTE);

  protected readonly visible = computed(() => {
    const c = this.carte();
    return 'cachee' in c ? null : c;
  });

  protected readonly image = computed(() => {
    const c = this.visible();
    return c ? this.habillage.image(c) : null;
  });

  protected readonly alt = computed(() => {
    const c = this.visible();
    if (!c) return '';
    if ('joker' in c) return 'joker';
    return `${VALEURS_FR[c.valeur] ?? c.valeur} de ${ENSEIGNES_FR[c.enseigne] ?? c.enseigne}`;
  });

  /** Joker : la carte qu'il remplace, en petit. */
  protected readonly badge = computed(() => {
    const c = this.visible();
    if (!c || !('joker' in c) || !c.represente) return null;
    const r = c.represente;
    return libelleCourt(r.slice(0, -1), r.slice(-1));
  });

  /** Le coin d'une carte très chevauchée : la valeur au-dessus de l'enseigne, en colonne étroite. */
  protected readonly index = computed(() => {
    const c = this.visible();
    if (!c || 'joker' in c || !this.indexRenforce()) return null;
    return {
      valeur: valeurCourte(c.valeur),
      enseigne: symbole(c.enseigne),
      rouge: c.enseigne === 'H' || c.enseigne === 'D',
    };
  });
}
