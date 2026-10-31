import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { VueTable } from '../../core/vue';
import { vueDebut, vueEnAttente, vueFactice, vueFinManche } from '../../../testing/vues';
import { Selection } from '../selection';
import { TableComponent } from './table.component';

function monter(vue: VueTable, selection?: Selection): ComponentFixture<TableComponent> {
  const fixture = TestBed.createComponent(TableComponent);
  fixture.componentRef.setInput('vue', vue);
  if (selection) fixture.componentRef.setInput('selection', selection);
  fixture.detectChanges();
  return fixture;
}

const racine = (f: ComponentFixture<TableComponent>) => f.nativeElement as HTMLElement;
const tous = (f: ComponentFixture<TableComponent>, sel: string) =>
  Array.from(racine(f).querySelectorAll<HTMLElement>(sel));

/** Sièges et zones du centre portent l'id reçu dans data-siege / data-zone. */
const siege = (f: ComponentFixture<TableComponent>, id: number) =>
  racine(f).querySelector<HTMLElement>(`.siege[data-siege="${id}"]`)!;

/** Une vue dont le premier groupe du centre est ciblable. */
function vueAvecCible(): VueTable {
  const vue = vueFinManche();
  vue.resultat = null;
  const zone = vue.zones.find((z) => z.type === 'combinaisons')!;
  zone.groupes[0].ciblable = true;
  return vue;
}

/** Une vue à 10 sièges de 13 cartes, construite à partir de la vue factice. */
function vueDixSieges(): VueTable {
  const vue = vueFactice();
  const modele = vue.sieges[1];
  vue.sieges = Array.from({ length: 10 }, (_, i) => ({
    ...modele,
    id: i,
    nom: i === 0 ? 'Toi' : `Ordinateur ${i}`,
    actif: i === 0,
  }));
  vue.zones = [
    ...vue.sieges.map((s) => ({
      id: `main-${s.id}`,
      type: 'main' as const,
      siege: s.id,
      libelle: s.nom,
      nombre: null,
      cartes: Array.from({ length: 13 }, (_, k) =>
        s.id === 0
          ? { id: `${k + 1}S-1`, valeur: String(k + 1), enseigne: 'S' }
          : { cachee: true as const },
      ),
      groupes: [],
    })),
    ...vue.zones.filter((z) => z.siege === null),
  ];
  vue.actions = [{ id: 'jouer', libelle: 'Jouer', cartes_min: 1, cartes_max: 1, cible: null }];
  return vue;
}

/** Centre x du siège et largeur de sa main. */
function mesures(f: ComponentFixture<TableComponent>, id: number) {
  const el = siege(f, id);
  return {
    x: parseFloat(el.style.left),
    main: parseFloat(el.querySelector<HTMLElement>('app-main')!.style.width),
  };
}

describe('TableComponent', () => {
  it('rend 4 sièges et met en avant le siège actif', () => {
    const f = monter(vueDebut());
    const sieges = tous(f, '.siege');
    expect(sieges).toHaveLength(4);
    expect(tous(f, '.siege.actif')).toHaveLength(1);
    expect(siege(f, 0).classList).toContain('actif');
    expect(siege(f, 0).querySelector('.nom')?.textContent?.trim()).toBe('Toi');
    expect(siege(f, 1).textContent).toContain('Cartes');
    expect(siege(f, 1).textContent).toContain('13');
  });

  it('place chaque siège dans la table', () => {
    const f = monter(vueDebut());
    for (const el of tous(f, '.siege')) {
      expect(el.style.left).toMatch(/px$/);
      expect(el.style.top).toMatch(/px$/);
    }
    // Le siège du joueur est en bas, le siège d'en face en haut.
    expect(parseFloat(siege(f, 0).style.top)).toBeGreaterThan(parseFloat(siege(f, 2).style.top));
  });

  it('la main du joueur est cliquable quand une action prend des cartes, celle des autres non', () => {
    const vue = vueEnAttente();
    const f = monter(vue);
    const recus: string[] = [];
    f.componentInstance.basculer.subscribe((id) => recus.push(id));

    const miennes = Array.from(siege(f, 0).querySelectorAll<HTMLElement>('.place'));
    expect(miennes.length).toBeGreaterThan(0);
    expect(miennes[0].getAttribute('role')).toBe('button');
    miennes[0].click();
    const premiere = vue.zones.find((z) => z.siege === 0)!.cartes[0];
    expect(recus).toEqual(['id' in premiere ? premiere.id : '']);

    const autres = Array.from(siege(f, 1).querySelectorAll<HTMLElement>('.place'));
    expect(autres.length).toBe(13);
    expect(autres[0].getAttribute('role')).toBeNull();
  });

  it("la main du joueur n'est pas cliquable si aucune action ne prend de carte", () => {
    const f = monter(vueDebut());
    const miennes = Array.from(siege(f, 0).querySelectorAll<HTMLElement>('.place'));
    expect(miennes[0].getAttribute('role')).toBeNull();
  });

  it('les zones sans siège sont au centre, dans l’ordre reçu, avec leur libellé', () => {
    const vue = vueDebut();
    const f = monter(vue);
    const attendus = vue.zones.filter((z) => z.siege === null).map((z) => z.libelle);
    const libelles = tous(f, '.centre .zone > .libelle').map((el) => el.textContent?.trim());
    expect(libelles).toEqual(attendus);
  });

  it('une pile montre sa carte du dessus ou un dos, et son nombre', () => {
    const vue = vueDebut();
    const f = monter(vue);
    const piles = vue.zones.filter((z) => z.type === 'pile');
    const fermee = piles.find((z) => z.cartes.length === 0)!;
    const ouverte = piles.find((z) => z.cartes.length > 0)!;
    const zoneFermee = racine(f).querySelector(`.zone[data-zone="${fermee.id}"]`)!;
    const zoneOuverte = racine(f).querySelector(`.zone[data-zone="${ouverte.id}"]`)!;
    expect(zoneFermee.querySelector('.dos')).not.toBeNull();
    expect(zoneFermee.querySelector('.nombre')?.textContent?.trim()).toBe(String(fermee.nombre));
    expect(zoneOuverte.querySelector('img')).not.toBeNull();
  });

  it('un groupe provisoire porte la classe « en attente »', () => {
    const f = monter(vueEnAttente());
    const groupes = tous(f, '.groupe');
    expect(groupes).toHaveLength(1);
    expect(groupes[0].classList).toContain('en-attente');
    expect(groupes[0].textContent).toContain('en attente');
    expect(groupes[0].getAttribute('role')).toBeNull();
  });

  it("un clic sur un groupe ciblable émet choisirCible('g1'), recliquer le désélectionne", () => {
    const vue = vueAvecCible();
    const f = monter(vue);
    const recus: (string | null)[] = [];
    f.componentInstance.choisirCible.subscribe((id) => recus.push(id));

    const g1 = racine(f).querySelector<HTMLElement>('.groupe[data-groupe="g1"]')!;
    expect(g1.getAttribute('role')).toBe('button');
    g1.click();
    expect(recus).toEqual(['g1']);

    f.componentRef.setInput('selection', { cartes: [], cible: 'g1' });
    f.detectChanges();
    expect(g1.classList).toContain('cible');
    expect(g1.getAttribute('aria-pressed')).toBe('true');
    g1.click();
    expect(recus).toEqual(['g1', null]);
  });

  it('un groupe non ciblable ne se choisit pas', () => {
    const f = monter(vueAvecCible());
    const recus: (string | null)[] = [];
    f.componentInstance.choisirCible.subscribe((id) => recus.push(id));
    const g2 = racine(f).querySelector<HTMLElement>('.groupe[data-groupe="g2"]')!;
    g2.click();
    expect(recus).toEqual([]);
    expect(g2.getAttribute('role')).toBeNull();
  });

  it('les autres types de zone ont un rendu générique : libellé et cartes', () => {
    const vue = vueFactice();
    vue.zones.push({
      id: 'z-pli',
      type: 'pli',
      siege: null,
      libelle: 'Pli en cours',
      nombre: null,
      cartes: [
        { id: 'AS-1', valeur: 'A', enseigne: 'S' },
        { id: 'KH-1', valeur: 'K', enseigne: 'H' },
      ],
      groupes: [],
    });
    const f = monter(vue);
    const zone = racine(f).querySelector('.zone[data-zone="z-pli"]')!;
    expect(zone.querySelector('.libelle')?.textContent?.trim()).toBe('Pli en cours');
    expect(zone.querySelectorAll('img')).toHaveLength(2);
  });

  it('avec un résultat, un panneau montre le titre et ses lignes', () => {
    const vue = vueFinManche();
    const f = monter(vue);
    const panneau = racine(f).querySelector('.resultat')!;
    expect(panneau.querySelector('h2')?.textContent?.trim()).toBe(vue.resultat!.titre);
    const entetes = Array.from(panneau.querySelectorAll('th')).map((el) => el.textContent?.trim());
    expect(entetes).toEqual(vue.resultat!.colonnes);
    const lignes = Array.from(panneau.querySelectorAll('tbody tr')).map((tr) =>
      Array.from(tr.querySelectorAll('td')).map((td) => td.textContent?.trim()),
    );
    expect(lignes).toEqual(vue.resultat!.lignes.map((l) => l.map(String)));
  });

  it('sans résultat, pas de panneau', () => {
    const f = monter(vueDebut());
    expect(racine(f).querySelector('.resultat')).toBeNull();
  });

  it('à 10 sièges, le siège du joueur passe devant ses voisins', () => {
    const f = monter(vueDixSieges());
    const z = tous(f, '.siege').map((el) => Number(el.style.zIndex));
    expect(z).toHaveLength(10);
    expect(z[0]).toBeGreaterThan(Math.max(...z.slice(1)));
  });

  it('à 10 sièges, la main du joueur ne passe pas sous ses voisins', () => {
    const f = monter(vueDixSieges());
    const joueur = mesures(f, 0);
    expect(joueur.main).toBeLessThan(0.7 * 800);
    for (const id of [1, 9]) {
      const voisin = mesures(f, id);
      expect(Math.abs(voisin.x - joueur.x) - voisin.main / 2).toBeGreaterThanOrEqual(
        joueur.main / 2,
      );
    }
  });

  it('à 4 sièges, la main du joueur garde toute sa largeur', () => {
    const f = monter(vueDebut());
    expect(mesures(f, 0).main).toBeCloseTo(0.7 * 800);
  });

  it('Entrée sur un groupe ciblable le choisit', () => {
    const f = monter(vueAvecCible());
    const recus: (string | null)[] = [];
    f.componentInstance.choisirCible.subscribe((id) => recus.push(id));
    const g1 = racine(f).querySelector<HTMLElement>('.groupe[data-groupe="g1"]')!;
    expect(g1.getAttribute('tabindex')).toBe('0');
    g1.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(recus).toEqual(['g1']);
  });

  it('une pile vide, nombre 0 ou inconnu, montre un emplacement vide et pas un dos', () => {
    for (const nombre of [0, null]) {
      const vue = vueFactice();
      vue.zones.push({
        id: 'z-vide',
        type: 'pile',
        siege: null,
        libelle: 'Vide',
        nombre,
        cartes: [],
        groupes: [],
      });
      const f = monter(vue);
      const zone = racine(f).querySelector('.zone[data-zone="z-vide"]')!;
      expect(zone.querySelector('.vide')).not.toBeNull();
      expect(zone.querySelector('.dos')).toBeNull();
    }
  });

  it('le titre du résultat a un id propre à chaque table', () => {
    const a = racine(monter(vueFinManche())).querySelector('h2')!;
    const b = racine(monter(vueFinManche())).querySelector('h2')!;
    expect(a.id).not.toBe(b.id);
    expect(a.closest('[role="dialog"]')!.getAttribute('aria-labelledby')).toBe(a.id);
  });
});
