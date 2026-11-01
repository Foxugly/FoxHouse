import { Routes } from '@angular/router';
import { AccueilPage } from './pages/accueil/accueil.page';
import { PartiePage } from './pages/partie/partie.page';
import { ReglesPage } from './pages/regles/regles.page';

export const routes: Routes = [
  { path: '', component: AccueilPage, title: 'FoxHouse' },
  { path: 'partie', component: PartiePage, title: 'Partie — FoxHouse' },
  { path: 'regles', component: ReglesPage, title: 'Règles — FoxHouse' },
  { path: '**', redirectTo: '' },
];
