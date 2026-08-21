import { Routes } from '@angular/router';

import { DashboardComponent } from './features/dashboard/dashboard.component';
import { TransactionDetailComponent } from './features/transactions/transaction-detail.component';
import { TransactionListComponent } from './features/transactions/transaction-list.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'transactions', component: TransactionListComponent },
  { path: 'transactions/:id', component: TransactionDetailComponent },
  { path: '**', redirectTo: '' },
];

