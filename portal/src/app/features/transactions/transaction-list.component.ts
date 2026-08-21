import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { combineLatest, switchMap } from 'rxjs';

import { TransactionService } from '../../core/services/transaction.service';
import { TransactionRowComponent } from '../../shared/components/transaction-row.component';

@Component({
  selector: 'app-transaction-list',
  standalone: true,
  imports: [TransactionRowComponent],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>Transacciones</h1>
          <p class="page__subtitle">Historial completo de ciclos compra → venta.</p>
        </div>
      </header>

      <section class="filters card">
        <label class="filter">
          <span>Modo</span>
          <select [value]="testMode() ?? ''" (change)="testMode.set(parseBool($event))">
            <option value="">Todos</option>
            <option value="true">Test</option>
            <option value="false">Real</option>
          </select>
        </label>
        <label class="filter">
          <span>Estado</span>
          <select [value]="status() ?? ''" (change)="status.set(parseString($event))">
            <option value="">Todos</option>
            <option value="OPEN">OPEN</option>
            <option value="CLOSED">CLOSED</option>
            <option value="CANCELED">CANCELED</option>
          </select>
        </label>
        <button class="btn" (click)="reload()">Aplicar filtros</button>
      </section>

      <section class="card table-wrap">
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
              <tr><td colspan="10" class="empty">Sin resultados con los filtros actuales.</td></tr>
            }
          </tbody>
        </table>
      </section>
    </div>
  `,
  styles: [`
    .page__header { margin-bottom: 1.5rem; }
    .page__subtitle { color: var(--muted); margin: 0.25rem 0 0; }
    .filters { display: flex; align-items: flex-end; gap: 1rem; padding: 1rem 1.2rem; margin-bottom: 1.5rem; }
    .filter { display: flex; flex-direction: column; gap: 0.35rem; }
    .filter span { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
    select { background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 0.45rem 0.7rem; font-size: 0.9rem; }
    .empty { text-align: center; color: var(--muted); padding: 2rem !important; }
    .th--num { text-align: right; }
  `],
})
export class TransactionListComponent {
  private readonly transactionService = inject(TransactionService);

  protected readonly testMode = signal<boolean | null>(null);
  protected readonly status = signal<string | null>(null);
  private readonly reloadTrigger = signal(0);

  protected readonly transactions = toSignal(
    combineLatest([
      toObservable(this.testMode),
      toObservable(this.status),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([testMode, status]) =>
        this.transactionService.list({ testMode, status, limit: 200 }),
      ),
    ),
  );

  parseBool(event: Event): boolean | null {
    const value = (event.target as HTMLSelectElement).value;
    if (value === '') return null;
    return value === 'true';
  }

  parseString(event: Event): string | null {
    const value = (event.target as HTMLSelectElement).value;
    return value === '' ? null : value;
  }

  reload(): void {
    this.reloadTrigger.update((n) => n + 1);
  }
}

