import { Routes } from '@angular/router';
import { AccueilPage } from './pages/accueil/accueil.page';
import { PartiePage } from './pages/partie/partie.page';

export const routes: Routes = [
  { path: '', component: AccueilPage, title: 'FoxHouse' },
  { path: 'partie', component: PartiePage, title: 'Partie — FoxHouse' },
  { path: '**', redirectTo: '' },
];
