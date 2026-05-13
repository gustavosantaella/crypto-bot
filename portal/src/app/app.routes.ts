import { Routes } from '@angular/router';
import { DashboardComponent }      from './pages/dashboard/dashboard.component';
import { HistoryComponent }         from './pages/history/history.component';
import { CancelledTradesComponent } from './pages/cancelled-trades/cancelled-trades.component';
import { StatisticsComponent }      from './pages/statistics/statistics';
import { PerformanceComponent }     from './pages/performance/performance.component';
import { SignalsComponent }         from './pages/signals/signals.component';

export const routes: Routes = [
  { path: '',                 component: DashboardComponent },
  { path: 'performance',      component: PerformanceComponent },
  { path: 'signals',          component: SignalsComponent },
  { path: 'history/rsi',      component: HistoryComponent },
  { path: 'trades/cancelled', component: CancelledTradesComponent },
  { path: 'statistics',       component: StatisticsComponent },
  { path: '**',               redirectTo: '' }
];
