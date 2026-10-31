import { computed, signal } from '@angular/core';
import { Etape } from '../../core/vue';

/** Temps d'affichage de chaque étape. */
export const DELAI_ETAPE = 700;

/** L'étape montrée au pas `pas` d'une relecture, ou `null` une fois toutes les étapes passées. */
export function etapeAuPas(etapes: readonly Etape[], pas: number): Etape | null {
  return pas >= 0 && pas < etapes.length ? etapes[pas] : null;
}

/**
 * Rejoue des étapes une à une, une toutes les `DELAI_ETAPE` ms. Tant qu'`enCours` est vrai, la page
 * montre `etape()` ; ensuite elle montre sa vue finale.
 */
export class Relecture {
  private readonly etapes = signal<readonly Etape[]>([]);
  private readonly pas = signal(0);
  private minuterie: ReturnType<typeof setTimeout> | null = null;

  readonly etape = computed(() => etapeAuPas(this.etapes(), this.pas()));
  readonly enCours = computed(() => this.etape() !== null);

  /** Démarre une relecture ; une relecture en cours est abandonnée. */
  lancer(etapes: readonly Etape[]): void {
    this.arreter();
    this.etapes.set(etapes);
    this.pas.set(0);
    this.programmer();
  }

  /** Saute à la fin. */
  passer(): void {
    this.arreter();
    this.etapes.set([]);
    this.pas.set(0);
  }

  /** Coupe la minuterie sans rien changer à l'affichage (destruction de la page). */
  arreter(): void {
    if (this.minuterie !== null) {
      clearTimeout(this.minuterie);
      this.minuterie = null;
    }
  }

  private programmer(): void {
    if (!this.enCours()) return;
    this.minuterie = setTimeout(() => {
      this.minuterie = null;
      this.pas.update((p) => p + 1);
      this.programmer();
    }, DELAI_ETAPE);
  }
}
