import { existsSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CarteVisible, Joker } from '../core/vue';
import { HABILLAGE_WEBISSO } from './habillage';

const visible = (valeur: string, enseigne: string): CarteVisible => ({
  id: `${valeur}${enseigne}-1`,
  valeur,
  enseigne,
});
const joker = (id: string): Joker => ({ id, joker: true });

describe('HABILLAGE_WEBISSO', () => {
  it('traduit valeurs et enseignes en noms de fichier', () => {
    expect(HABILLAGE_WEBISSO.image(visible('10', 'H'))).toBe('/cartes/webisso/10_of_hearts.svg');
    expect(HABILLAGE_WEBISSO.image(visible('Q', 'S'))).toBe('/cartes/webisso/queen_of_spades.svg');
    expect(HABILLAGE_WEBISSO.image(visible('A', 'D'))).toBe('/cartes/webisso/ace_of_diamonds.svg');
    expect(HABILLAGE_WEBISSO.image(visible('J', 'C'))).toBe('/cartes/webisso/jack_of_clubs.svg');
    expect(HABILLAGE_WEBISSO.image(visible('K', 'C'))).toBe('/cartes/webisso/king_of_clubs.svg');
  });

  it('associe les jokers 1 et 3 au noir, 2 et 4 au rouge', () => {
    expect(HABILLAGE_WEBISSO.image(joker('JK-1'))).toBe('/cartes/webisso/black_joker.svg');
    expect(HABILLAGE_WEBISSO.image(joker('JK-3'))).toBe('/cartes/webisso/black_joker.svg');
    expect(HABILLAGE_WEBISSO.image(joker('JK-2'))).toBe('/cartes/webisso/red_joker.svg');
    expect(HABILLAGE_WEBISSO.image(joker('JK-4'))).toBe('/cartes/webisso/red_joker.svg');
  });

  it('vise des fichiers qui existent tous', () => {
    const dossier = 'public/cartes/webisso/';
    const valeurs = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
    const cartes = ['S', 'H', 'D', 'C'].flatMap((e) => valeurs.map((v) => visible(v, e)));
    const toutes = [...cartes, joker('JK-1'), joker('JK-2')];
    for (const c of toutes) {
      const fichier = HABILLAGE_WEBISSO.image(c).replace('/cartes/webisso/', dossier);
      expect(existsSync(fichier), fichier).toBe(true);
    }
    expect(readdirSync(dossier).filter((f) => f.endsWith('.svg')).length).toBe(54);
  });
});
