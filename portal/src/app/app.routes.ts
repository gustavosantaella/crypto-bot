import { Routes } from '@angular/router';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { HistoryComponent } from './pages/history/history.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'history/rsi', component: HistoryComponent },
  { path: '**', redirectTo: '' }
];
