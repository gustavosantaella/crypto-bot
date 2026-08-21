import { Component, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { TransactionService } from '../../core/services/transaction.service';
import { DateTimePipe } from '../../shared/pipes/datetime.pipe';
import { PercentPipe } from '../../shared/pipes/percent.pipe';
import { UsdtPipe } from '../../shared/pipes/usdt.pipe';

@Component({
  selector: 'app-transaction-detail',
  standalone: true,
  imports: [RouterLink, UsdtPipe, PercentPipe, DateTimePipe],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <a class="link" routerLink="/transactions">← Transacciones</a>
          <h1>Transacción #{{ id() }}</h1>
        </div>
        <span class="badge" [class.badge--open]="tx()?.status === 'OPEN'"
                           [class.badge--closed]="tx()?.status === 'CLOSED'"
                           [class.badge--canceled]="tx()?.status === 'CANCELED'">
          {{ tx()?.status }}
        </span>
      </header>

      @if (tx(); as t) {
        <section class="grid">
          <div class="card">
            <h2>Compra</h2>
            <dl class="detail">
              <dt>Precio</dt><dd>{{ t.buy_price | usdt }}</dd>
              <dt>Cantidad</dt><dd>{{ t.buy_quantity }} {{ t.symbol.replace('USDT', '') }}</dd>
              <dt>Gasto total</dt><dd>{{ t.buy_quote | usdt }}</dd>
              <dt>Orden Binance</dt><dd>#{{ t.buy_order_id }}</dd>
              <dt>Fecha</dt><dd>{{ t.buy_time | fecha }}</dd>
            </dl>
          </div>
          <div class="card">
            <h2>Venta</h2>
            @if (t.sell_price != null) {
              <dl class="detail">
                <dt>Precio</dt><dd>{{ t.sell_price | usdt }}</dd>
                <dt>Cantidad</dt><dd>{{ t.sell_quantity }} {{ t.symbol.replace('USDT', '') }}</dd>
                <dt>Ingreso total</dt><dd>{{ t.sell_quote | usdt }}</dd>
                <dt>Orden Binance</dt><dd>#{{ t.sell_order_id }}</dd>
                <dt>Fecha</dt><dd>{{ t.sell_time | fecha }}</dd>
              </dl>
            } @else {
              <p class="empty">La transacción sigue abierta (aún no se vende).</p>
            }
          </div>
          <div class="card">
            <h2>Resultado</h2>
            <dl class="detail">
              <dt>Ganancia</dt>
              <dd [class.text--ok]="(t.profit ?? 0) >= 0" [class.text--loss]="(t.profit ?? 0) < 0">
                {{ t.profit != null ? (t.profit | usdt) : '—' }}
              </dd>
              <dt>Rentabilidad</dt>
              <dd [class.text--ok]="(t.profit_pct ?? 0) >= 0" [class.text--loss]="(t.profit_pct ?? 0) < 0">
                {{ t.profit_pct != null ? (t.profit_pct | pct) : '—' }}
              </dd>
              <dt>Modo</dt>
              <dd>
                <span class="badge" [class.badge--test]="t.test_mode" [class.badge--real]="!t.test_mode">
                  {{ t.test_mode ? 'TEST' : 'REAL' }}
                </span>
              </dd>
              <dt>Creado</dt><dd>{{ t.created_at | fecha }}</dd>
            </dl>
          </div>
        </section>
      } @else {
        <p class="empty card">Transacción no encontrada o aún cargando…</p>
      }
    </div>
  `,
  styles: [`
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
    .page__header h1 { margin: 0.5rem 0 0; }
    .link { color: var(--accent); text-decoration: none; font-size: 0.9rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem; }
    .card h2 { font-size: 1rem; margin: 0 0 0.75rem; }
    .detail { display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem; margin: 0; }
    .detail dt { color: var(--muted); font-size: 0.85rem; }
    .detail dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
    .empty { color: var(--muted); padding: 1rem; }
    .badge { padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
    .badge--open { background: var(--warn-bg); color: var(--warn); }
    .badge--closed { background: var(--ok-bg); color: var(--ok); }
    .badge--canceled { background: var(--danger-bg); color: var(--danger); }
    .badge--test { background: rgba(148, 163, 184, 0.18); color: #94a3b8; }
    .badge--real { background: rgba(34, 211, 238, 0.15); color: #22d3ee; }
    .text--ok { color: var(--ok); }
    .text--loss { color: var(--danger); }
  `],
})
export class TransactionDetailComponent {
  private readonly transactionService = inject(TransactionService);

  /** Id de la transacción, inyectado desde la ruta (string). */
  readonly id = input.required<string>();

  /** Reacciona a los cambios del input (evaluación perezosa y reactiva). */
  protected readonly tx = toSignal(
    toObservable(this.id).pipe(
      switchMap((id) => this.transactionService.get(Number(id))),
    ),
  );
}
