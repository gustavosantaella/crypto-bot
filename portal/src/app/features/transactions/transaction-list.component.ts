import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { combineLatest, switchMap } from 'rxjs';

import { EnvironmentService } from '../../core/services/environment.service';
import { EventService } from '../../core/services/event.service';
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
          <p class="page__subtitle">
            Historial de ciclos · {{ marketType() === 'FUTURES' ? 'Futuros' : 'Spot' }} ·
            {{ testMode() ? 'Testnet' : 'Producción' }}
          </p>
        </div>
      </header>

      <section class="filters card">
        <label class="filter">
          <span>Mercado</span>
          <select [value]="marketType()" (change)="setMarket($event)">
            <option value="SPOT">SPOT</option>
            <option value="FUTURES">FUTURES</option>
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
              <th>ID</th><th>Par</th><th>Mercado</th><th>Lado</th><th>Estado</th><th>Modo</th>
              <th class="th--num">Compra</th><th>Fecha compra</th>
              <th class="th--num">Venta</th><th>Fecha venta</th>
              <th class="th--num">Ganancia</th><th class="th--num">%</th>
            </tr>
          </thead>
          <tbody>
            @for (tx of transactions(); track tx.id) {
              <tr><app-transaction-row [tx]="tx" /></tr>
            } @empty {
              <tr><td colspan="12" class="empty">Sin resultados con los filtros actuales.</td></tr>
            }
          </tbody>
        </table>
      </section>
    </div>
  `,
  styles: [`
    .page__header { margin-bottom: 1.5rem; }
    .page__subtitle { color: var(--muted); margin: 0.25rem 0 0; }
    .filters { display: flex; align-items: flex-end; gap: 1rem; padding: 1rem 1.2rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .filter { display: flex; flex-direction: column; gap: 0.35rem; }
    .filter span { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
    select { background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 0.45rem 0.7rem; font-size: 0.9rem; }
    .empty { text-align: center; color: var(--muted); padding: 2rem !important; }
    .th--num { text-align: right; }
  `],
})
export class TransactionListComponent {
  private readonly transactionService = inject(TransactionService);
  private readonly environmentService = inject(EnvironmentService);
  private readonly eventService = inject(EventService);

  /** Ambiente del switch del sidebar (true=Testnet). */
  protected readonly testMode = this.environmentService.testMode$;

  /** Mercado seleccionado (SPOT | FUTURES). */
  protected readonly marketType = this.environmentService.marketType$;

  protected readonly status = signal<string | null>(null);
  private readonly reloadTrigger = signal(0);

  constructor() {
    // Recarga la lista en tiempo real cuando el bot compra/vende.
    this.eventService.changes$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.reload());
  }

  protected readonly transactions = toSignal(
    combineLatest([
      toObservable(this.testMode),
      toObservable(this.marketType),
      toObservable(this.status),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([testMode, marketType, status]) =>
        this.transactionService.list({ testMode, marketType, status, limit: 200 }),
      ),
    ),
  );

  parseString(event: Event): string | null {
    const value = (event.target as HTMLSelectElement).value;
    return value === '' ? null : value;
  }

  setMarket(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as 'SPOT' | 'FUTURES';
    this.environmentService.setMarketType(value);
  }

  reload(): void {
    this.reloadTrigger.update((n) => n + 1);
  }
}

