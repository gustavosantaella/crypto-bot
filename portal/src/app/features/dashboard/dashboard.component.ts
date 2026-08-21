import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { combineLatest, switchMap } from 'rxjs';

import { TransactionService } from '../../core/services/transaction.service';
import { TransactionRowComponent } from '../../shared/components/transaction-row.component';
import { UsdtPipe } from '../../shared/pipes/usdt.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, TransactionRowComponent, UsdtPipe],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>Panel de control</h1>
          <p class="page__subtitle">Resumen del bot: compra barato, vende caro.</p>
        </div>
        <button class="btn" (click)="refresh()">Refrescar</button>
      </header>

      <section class="stats-grid">
        <div class="stat-card">
          <span class="stat-card__label">Total de ciclos</span>
          <span class="stat-card__value">{{ stats()?.total ?? 0 }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Cerrados</span>
          <span class="stat-card__value text--ok">{{ stats()?.closed ?? 0 }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Abiertos</span>
          <span class="stat-card__value text--warn">{{ stats()?.open ?? 0 }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Ganancia total</span>
          <span class="stat-card__value" [class.text--ok]="(stats()?.total_profit ?? 0) >= 0"
                                      [class.text--loss]="(stats()?.total_profit ?? 0) < 0">
            {{ stats()?.total_profit ?? 0 | usdt }}
          </span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Ganancia promedio</span>
          <span class="stat-card__value">{{ stats()?.avg_profit ?? 0 | usdt }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Test / Real</span>
          <span class="stat-card__value">
            {{ stats()?.test_mode ?? 0 }} / {{ stats()?.real ?? 0 }}
          </span>
        </div>
      </section>

      <section class="card">
        <header class="card__header">
          <h2>Últimas transacciones</h2>
          <a class="link" routerLink="/transactions">Ver todas →</a>
        </header>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th><th>Par</th><th>Estado</th><th>Modo</th>
                <th class="th--num">Compra</th><th>Fecha compra</th>
                <th class="th--num">Venta</th><th>Fecha venta</th>
                <th class="th--num">Ganancia</th><th class="th--num">%</th>
              </tr>
            </thead>
            <tbody>
              @for (tx of transactions(); track tx.id) {
                <tr><app-transaction-row [tx]="tx" /></tr>
              } @empty {
                <tr><td colspan="10" class="empty">No hay transacciones todavía.</td></tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.5rem; }
    .page__subtitle { color: var(--muted); margin: 0.25rem 0 0; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.1rem; display: flex; flex-direction: column; gap: 0.35rem; }
    .stat-card__label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-card__value { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
    .card__header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.2rem; border-bottom: 1px solid var(--border); }
    .card__header h2 { font-size: 1.05rem; margin: 0; }
    .link { color: var(--accent); text-decoration: none; font-size: 0.9rem; }
    .empty { text-align: center; color: var(--muted); padding: 2rem !important; }
    .th--num { text-align: right; }
    .text--ok { color: var(--ok); }
    .text--warn { color: var(--warn); }
    .text--loss { color: var(--danger); }
  `],
})
export class DashboardComponent {
  private readonly transactionService = inject(TransactionService);
  private readonly reloadTrigger = signal(0);

  protected readonly stats = toSignal(
    combineLatest([toObservable(this.reloadTrigger)]).pipe(
      switchMap(() => this.transactionService.getStats()),
    ),
  );
  protected readonly transactions = toSignal(
    combineLatest([toObservable(this.reloadTrigger)]).pipe(
      switchMap(() => this.transactionService.list({ limit: 10 })),
    ),
  );

  refresh(): void {
    this.reloadTrigger.update((n) => n + 1);
  }
}

