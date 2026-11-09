import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { vueEnAttente } from '../../../testing/vues';
import { MenuComponent } from './menu.component';

describe('MenuComponent', () => {
  it("affiche les lignes du menu, sans aucun bouton : c'est un panneau d'informations", () => {
    const vue = vueEnAttente();
    const f = TestBed.createComponent(MenuComponent);
    f.componentRef.setInput('vue', vue);
    f.detectChanges();
    const racine = f.nativeElement as HTMLElement;
    const lignes = Array.from(racine.querySelectorAll('.ligne')).map((el) => [
      el.querySelector('dt')?.textContent?.trim(),
      el.querySelector('dd')?.textContent?.trim(),
    ]);
    expect(lignes).toEqual(vue.menu.map((l) => [l.libelle, String(l.valeur)]));
    expect(racine.querySelectorAll('button').length).toBe(0);
  });
});
