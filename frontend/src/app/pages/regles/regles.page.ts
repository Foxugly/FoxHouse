import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { ApiService, ErreurApi } from '../../core/api.service';
import { DescriptionJeu } from '../../core/vue';

/** Le rappel des règles : un onglet par jeu, l'onglet choisi gardé dans l'URL (`?jeu=<code>`). */
@Component({
  selector: 'app-regles-page',
  imports: [RouterLink],
  templateUrl: './regles.page.html',
  styleUrl: './regles.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReglesPage {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly hote = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly jeux = signal<DescriptionJeu[] | null>(null);
  protected readonly erreurChargement = signal<string | null>(null);
  private readonly codeDemande = toSignal(this.route.queryParamMap.pipe(map((p) => p.get('jeu'))), {
    initialValue: null,
  });
  /** Le jeu de l'URL, sinon le premier ; un code inconnu montre aussi le premier. */
  protected readonly jeu = computed(() => {
    const jeux = this.jeux() ?? [];
    return jeux.find((j) => j.code === this.codeDemande()) ?? jeux[0] ?? null;
  });

  constructor() {
    this.api
      .jeux()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (jeux) => this.jeux.set(jeux),
        error: (e: unknown) => {
          if (!(e instanceof ErreurApi)) throw e;
          this.erreurChargement.set(e.message);
        },
      });
  }

  protected choisir(code: string): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { jeu: code },
      replaceUrl: true,
    });
  }

  /** Flèches, Début et Fin passent d'un onglet à l'autre (motif « tabs » de l'ARIA). */
  protected clavier(evenement: KeyboardEvent): void {
    const jeux = this.jeux() ?? [];
    const courant = jeux.findIndex((j) => j.code === this.jeu()?.code);
    const cible = {
      ArrowRight: courant + 1,
      ArrowLeft: courant - 1,
      Home: 0,
      End: jeux.length - 1,
    }[evenement.key];
    if (cible === undefined || jeux.length === 0) return;
    evenement.preventDefault();
    const suivant = jeux[(cible + jeux.length) % jeux.length];
    this.choisir(suivant.code);
    this.hote.nativeElement.querySelector<HTMLElement>(`#onglet-${suivant.code}`)?.focus();
  }
}
