import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, combineLatest, of, switchMap } from 'rxjs';

import { AssetBalance, AccountBalance } from '../../core/models/balance.model';
import { BalanceService } from '../../core/services/balance.service';
import { EnvironmentService } from '../../core/services/environment.service';
import { EventService } from '../../core/services/event.service';
import { TransactionService } from '../../core/services/transaction.service';
import { TransactionRowComponent } from '../../shared/components/transaction-row.component';
import { NumPipe } from '../../shared/pipes/num.pipe';
import { UsdtPipe } from '../../shared/pipes/usdt.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, TransactionRowComponent, UsdtPipe, NumPipe],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>Panel de control</h1>
          <p class="page__subtitle">Resumen del bot: compra barato, vende caro.</p>
        </div>
        <div class="header__actions">
          <span class="sse-badge" [class.sse-badge--on]="sseConnected() === true"
                                  [class.sse-badge--off]="sseConnected() === false">
            {{ sseConnected() === true ? '● En vivo' : (sseConnected() === false ? '● Reconectando' : '● Conectando') }}
          </span>
          <button class="btn" (click)="refresh()">Refrescar</button>
        </div>
      </header>

      <!-- Cuenta spot -->
      <section class="card section">
        <header class="card__header">
          <h2>Cuenta spot — {{ testMode() ? 'Testnet' : 'Producción' }}</h2>
        </header>
        @if (balance(); as b) {
          <div class="balance-grid">
            @for (asset of mainAssets(b); track asset.asset) {
              <div class="stat-card">
                <span class="stat-card__label">{{ asset.asset }}</span>
                <span class="stat-card__value stat-card__value--small">{{ asset.free | num }}</span>
              </div>
            }
            @if (otherAssets(b).length > 0) {
              <div class="stat-card">
                <span class="stat-card__label">Otros</span>
                <div class="chips">
                  @for (a of otherAssets(b); track a.asset) {
                    <span class="chip">{{ a.asset }} {{ a.free | num }}</span>
                  }
                </div>
              </div>
            }
          </div>
        } @else if (balanceError(); as err) {
          <p class="empty">⚠️ No se pudo consultar el balance de este ambiente:<br />{{ err }}</p>
        } @else {
          <p class="empty">Cargando balance…</p>
        }
      </section>

      <!-- Stats generales -->
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
          <span class="stat-card__label">Ganadas / Perdidas</span>
          <span class="stat-card__value">
            {{ testMode() ? (stats()?.wins_test ?? 0) : (stats()?.wins_real ?? 0) }} /
            {{ testMode() ? (stats()?.losses_test ?? 0) : (stats()?.losses_real ?? 0) }}
          </span>
        </div>
      </section>

      <!-- Últimas transacciones -->
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
    .header__actions { display: flex; align-items: center; gap: 0.75rem; }
    .sse-badge { font-size: 0.8rem; font-weight: 700; color: var(--muted); }
    .sse-badge--on { color: var(--ok); }
    .sse-badge--off { color: var(--warn); }
    .section { margin-bottom: 1.5rem; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .balance-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; padding: 1.2rem; }
    .stat-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.1rem; display: flex; flex-direction: column; gap: 0.35rem; }
    .stat-card__label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-card__value { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .stat-card__value--small { font-size: 1.1rem; }
    .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
    .chip { background: var(--bg); border: 1px solid var(--border); border-radius: 999px; padding: 0.15rem 0.55rem; font-size: 0.78rem; color: var(--muted); font-variant-numeric: tabular-nums; }
    .result-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .result-card { padding: 1.1rem 1.2rem; }
    .result-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; }
    .result-card__count { color: var(--muted); font-size: 0.85rem; }
    .result-card__profit { font-size: 1.7rem; font-weight: 800; margin: 0.25rem 0; font-variant-numeric: tabular-nums; }
    .result-card__detail { color: var(--muted); margin: 0; font-size: 0.85rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
    .card__header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.2rem; border-bottom: 1px solid var(--border); }
    .card__header h2 { font-size: 1.05rem; margin: 0; }
    .badge { padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.03em; }
    .badge--test { background: rgba(148, 163, 184, 0.18); color: #94a3b8; }
    .badge--real { background: rgba(34, 211, 238, 0.15); color: #22d3ee; }
    .link { color: var(--accent); text-decoration: none; font-size: 0.9rem; }
    .empty { text-align: center; color: var(--muted); padding: 2rem !important; margin: 0; }
    .th--num { text-align: right; }
    .text--ok { color: var(--ok); }
    .text--warn { color: var(--warn); }
    .text--loss { color: var(--danger); }
  `],
})
export class DashboardComponent {
  private readonly transactionService = inject(TransactionService);
  private readonly balanceService = inject(BalanceService);
  private readonly environmentService = inject(EnvironmentService);
  private readonly eventService = inject(EventService);
  private readonly reloadTrigger = signal(0);

  /** Ambiente seleccionado en el switch del sidebar (true=Testnet). */
  protected readonly testMode = this.environmentService.testMode$;

  /** Estado de la conexión SSE (null mientras conecta, true/false después). */
  protected readonly sseConnected = toSignal(this.eventService.connection$);

  constructor() {
    // Actualiza en tiempo real cuando el backend registra una operación.
    this.eventService.changes$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.refresh());
  }

  protected readonly stats = toSignal(
    combineLatest([toObservable(this.testMode), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode]) => this.transactionService.getStats(testMode)),
    ),
  );
  protected readonly transactions = toSignal(
    combineLatest([toObservable(this.testMode), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode]) => this.transactionService.list({ testMode, limit: 10 })),
    ),
  );
  protected readonly balance = toSignal(
    combineLatest([toObservable(this.testMode), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode]) => {
        this.balanceError.set(null);
        return this.balanceService.get(testMode).pipe(
          catchError((err) => {
            const detail = err?.error?.detail ?? err?.message ?? 'error desconocido';
            this.balanceError.set(detail);
            return of(null);
          }),
        );
      }),
    ),
  );

  /** Mensaje de error al consultar el balance (si falla). */
  protected readonly balanceError = signal<string | null>(null);

  /** Activos principales del par (p. ej. BTC y USDT) + 2 extras con saldo. */
  mainAssets(balance: AccountBalance): AssetBalance[] {
    const wanted = [balance.currency, 'USDT'];
    const main = balance.balances.filter((x) => wanted.includes(x.asset));
    const rest = balance.balances.filter((x) => !wanted.includes(x.asset));
    return [...main, ...rest.slice(0, 2)];
  }

  /** Resto de activos con saldo (máx. 5 chips para no saturar la UI). */
  otherAssets(balance: AccountBalance): AssetBalance[] {
    const wanted = [balance.currency, 'USDT'];
    const rest = balance.balances.filter((x) => !wanted.includes(x.asset));
    return rest.slice(0, 5);
  }

  refresh(): void {
    this.reloadTrigger.update((n) => n + 1);
  }
}

