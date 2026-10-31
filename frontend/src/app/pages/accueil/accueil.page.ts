import { Location } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  linkedSignal,
  signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ApiService, ErreurApi } from '../../core/api.service';
import { DescriptionJeu, DescriptionOption } from '../../core/vue';
import { prendreEtatNavigation } from '../etat-navigation';

type Valeurs = Record<string, unknown>;

/** Les valeurs de départ du formulaire : le défaut de chaque option. */
export function valeursParDefaut(jeu: DescriptionJeu | null): Valeurs {
  return Object.fromEntries((jeu?.options ?? []).map((o) => [o.code, o.defaut]));
}

/** Le nombre de joueurs proposé : un adversaire de plus que le minimum, dans les bornes. */
export function joueursParDefaut(jeu: DescriptionJeu | null): number {
  return jeu ? Math.min(jeu.min_joueurs + 1, jeu.max_joueurs) : 0;
}

/** Un entier saisi, ramené dans les bornes de l'option ; `null` si la saisie n'est pas un nombre. */
export function entierBorne(option: DescriptionOption, saisie: string): number | null {
  const n = Math.round(Number(saisie));
  if (saisie.trim() === '' || !Number.isFinite(n)) return null;
  const min = option.minimum ?? -Infinity;
  const max = option.maximum ?? Infinity;
  return Math.min(max, Math.max(min, n));
}

@Component({
  selector: 'app-accueil-page',
  imports: [RouterLink],
  templateUrl: './accueil.page.html',
  styleUrl: './accueil.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccueilPage {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  /** Le message laissé par la page précédente (« Aucune partie en cours. »). */
  protected readonly message = signal(
    (prendreEtatNavigation(inject(Location), 'message') as string | undefined) ?? null,
  );
  protected readonly jeux = signal<DescriptionJeu[] | null>(null);
  protected readonly partieEnCours = signal(false);
  protected readonly codeChoisi = signal<string | null>(null);
  protected readonly jeu = computed(() => {
    const jeux = this.jeux() ?? [];
    return jeux.find((j) => j.code === this.codeChoisi()) ?? jeux[0] ?? null;
  });
  /** Changer de jeu remet son formulaire à ses valeurs par défaut. */
  protected readonly valeurs = linkedSignal(() => valeursParDefaut(this.jeu()));
  protected readonly nbJoueurs = linkedSignal(() => joueursParDefaut(this.jeu()));
  protected readonly nombresDeJoueurs = computed(() => {
    const jeu = this.jeu();
    if (!jeu) return [];
    return Array.from(
      { length: jeu.max_joueurs - jeu.min_joueurs + 1 },
      (_, i) => jeu.min_joueurs + i,
    );
  });
  /** La création est partie et attend sa réponse. */
  protected readonly envoi = signal(false);
  protected readonly erreur = signal<string | null>(null);
  protected readonly erreurChargement = signal<string | null>(null);

  constructor() {
    this.api.jeux().subscribe({
      next: (jeux) => this.jeux.set(jeux),
      error: (e: unknown) => {
        if (!(e instanceof ErreurApi)) throw e;
        this.erreurChargement.set(e.message);
      },
    });
    // Sans réponse, l'accueil propose seulement une nouvelle partie.
    this.api.courante().subscribe({
      next: (partie) => this.partieEnCours.set(partie !== null),
      error: () => this.partieEnCours.set(false),
    });
  }

  protected definir(code: string, valeur: unknown): void {
    this.valeurs.update((v) => ({ ...v, [code]: valeur }));
  }

  protected choisirOption(option: DescriptionOption, evenement: Event): void {
    const index = (evenement.target as HTMLSelectElement).selectedIndex;
    const choix = option.choix?.[index];
    if (choix) this.definir(option.code, choix.valeur);
  }

  protected cocher(option: DescriptionOption, evenement: Event): void {
    this.definir(option.code, (evenement.target as HTMLInputElement).checked);
  }

  protected saisirEntier(option: DescriptionOption, evenement: Event): void {
    const champ = evenement.target as HTMLInputElement;
    const valeur = entierBorne(option, champ.value) ?? (this.valeurs()[option.code] as number);
    // Le champ affiche la valeur retenue, même si le signal n'a pas changé.
    champ.value = String(valeur);
    this.definir(option.code, valeur);
  }

  protected choisirNbJoueurs(evenement: Event): void {
    this.nbJoueurs.set(Number((evenement.target as HTMLSelectElement).value));
  }

  protected commencer(evenement: Event): void {
    evenement.preventDefault();
    const jeu = this.jeu();
    if (this.envoi() || !jeu) return;
    this.envoi.set(true);
    this.erreur.set(null);
    this.api.creer(jeu.code, this.nbJoueurs(), this.valeurs()).subscribe({
      next: (partie) => void this.router.navigate(['/partie'], { state: { partie } }),
      error: (e: unknown) => {
        this.envoi.set(false);
        if (!(e instanceof ErreurApi)) throw e;
        this.erreur.set(e.message);
      },
    });
  }
}
