import { Carte, VueTable } from '../../core/vue';

/** Temps pendant lequel un pli terminé reste sur la table avant d'être ramassé. */
export const DELAI_PLI = 5000;

/** Une carte d'un pli, avec le nom de celui qui l'a jouée. */
export interface CartePli {
  nom: string;
  carte: Carte;
}

/**
 * Le pli est terminé quand chaque siège a sa carte dans sa zone « pli » : la vue le montre encore
 * tant que la carte suivante n'est pas jouée. Sans zone « pli », jamais.
 */
export function pliTermine(vue: VueTable): boolean {
  const plis = vue.zones.filter((z) => z.type === 'pli');
  return plis.length > 0 && plis.every((z) => z.cartes.length > 0);
}

/** Les cartes du pli terminé, dans l'ordre des sièges ; `null` si le pli n'est pas terminé. */
export function cartesDuPli(vue: VueTable): CartePli[] | null {
  if (!pliTermine(vue)) return null;
  return vue.zones
    .filter((z) => z.type === 'pli')
    .flatMap((z) => {
      const nom = vue.sieges.find((s) => s.id === z.siege)?.nom ?? z.libelle;
      return z.cartes.map((carte) => ({ nom, carte }));
    });
}

/** La même vue, ses zones « pli » vidées : la table une fois le pli ramassé. */
export function sansPli(vue: VueTable): VueTable {
  return {
    ...vue,
    zones: vue.zones.map((z) => (z.type === 'pli' ? { ...z, cartes: [] } : z)),
  };
}
