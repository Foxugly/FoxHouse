import { readdirSync, readFileSync, statSync } from 'node:fs';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { Action } from '../core/vue';
import { vueFactice } from '../../testing/vues';
import { MenuComponent } from './menu/menu.component';
import { TableComponent } from './table/table.component';

/**
 * Mots propres à un jeu, écrits en morceaux pour que ce fichier ne les contienne pas lui-même.
 * Les accents sont retirés avant la recherche : un mot accentué est trouvé sans ses accents.
 */
const MOTS_INTERDITS = [
  'ra' + 'mi',
  'pio' + 'cher',
  'po' + 'ser',
  'def' + 'ausse',
  'brou' + 'illon',
];
/** Le tapis et le cœur ne connaissent aucun jeu ; les pages non plus. */
const DOSSIERS = ['src/app/tapis', 'src/app/core', 'src/app/pages'];

function fichiers(dossier: string): string[] {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = `${dossier}/${nom}`;
    return statSync(chemin).isDirectory() ? fichiers(chemin) : [chemin];
  });
}

const sansAccents = (texte: string) => texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

describe('généricité du tapis', () => {
  it('la table rend la vue du jeu factice', () => {
    const fixture = TestBed.createComponent(TableComponent);
    fixture.componentRef.setInput('vue', vueFactice());
    fixture.detectChanges();
    const racine = fixture.nativeElement as HTMLElement;
    expect(racine.querySelectorAll('.siege').length).toBe(3);
    expect(racine.querySelectorAll('img').length).toBeGreaterThan(0);
  });

  it('le menu rend la vue du jeu factice et « Retourner » est cliquable', () => {
    const fixture = TestBed.createComponent(MenuComponent);
    fixture.componentRef.setInput('vue', vueFactice());
    fixture.detectChanges();
    const emises: Action[] = [];
    fixture.componentInstance.agir.subscribe((a) => emises.push(a));
    const bouton = (fixture.nativeElement as HTMLElement).querySelector('button')!;
    expect(bouton.textContent?.trim()).toBe('Retourner');
    expect(bouton.disabled).toBe(false);
    bouton.click();
    expect(emises.map((a) => a.id)).toEqual(['retourner']);
  });

  it('aucun fichier du tapis, du cœur ni des pages ne nomme un jeu ou ses actions', () => {
    const trouves = DOSSIERS.flatMap(fichiers).flatMap((chemin) => {
      const texte = sansAccents(readFileSync(chemin, 'utf8'));
      return MOTS_INTERDITS.filter((mot) => texte.includes(mot)).map((mot) => `${chemin} : ${mot}`);
    });
    expect(DOSSIERS.flatMap(fichiers).length).toBeGreaterThan(10);
    expect(trouves).toEqual([]);
  });
});
