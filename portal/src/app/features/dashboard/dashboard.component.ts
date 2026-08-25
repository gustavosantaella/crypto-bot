import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, combineLatest, of, switchMap } from 'rxjs';

import { AssetBalance, AccountBalance } from '../../core/models/balance.model';
import { MarketAnalysis } from '../../core/models/market-analysis.model';
import { AnalysisService } from '../../core/services/analysis.service';
import { BalanceService } from '../../core/services/balance.service';
import { EnvironmentService } from '../../core/services/environment.service';
import { EventService } from '../../core/services/event.service';
import { MarketSignalService } from '../../core/services/market-signal.service';
import { TransactionService } from '../../core/services/transaction.service';
import { TransactionRowComponent } from '../../shared/components/transaction-row.component';
import { NumPipe } from '../../shared/pipes/num.pipe';
import { PercentPipe } from '../../shared/pipes/percent.pipe';
import { UsdtPipe } from '../../shared/pipes/usdt.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, TransactionRowComponent, UsdtPipe, NumPipe, PercentPipe],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>Panel de control</h1>
          <p class="page__subtitle">
            Bot de trading · {{ marketType() === 'FUTURES' ? 'Futuros USDT-M' : 'Spot' }} ·
            {{ testMode() ? 'Testnet' : 'Producción' }}
          </p>
        </div>
        <div class="header__actions">
          <span class="sse-badge" [class.sse-badge--on]="sseConnected() === true"
                                  [class.sse-badge--off]="sseConnected() === false">
            {{ sseConnected() === true ? '● En vivo' : (sseConnected() === false ? '● Reconectando' : '● Conectando') }}
          </span>
          <button class="btn" (click)="refresh()">Refrescar</button>
        </div>
      </header>

      <!-- Señal de mercado (LONG / SHORT / NEUTRAL) -->
      <section class="card section">
        <header class="card__header">
          <h2>Señal de mercado — {{ signal()?.symbol ?? '…' }} <span class="muted">({{ signal()?.interval ?? '1m' }})</span></h2>
          <span class="badge badge--signal" [class.badge--ok]="signal()?.recommendation === 'LONG'"
                                           [class.badge--danger]="signal()?.recommendation === 'SHORT'"
                                           [class.badge--neutral]="signal()?.recommendation === 'NEUTRAL'">
            {{ signal()?.recommendation ?? '…' }}
          </span>
        </header>

        @if (signal(); as s) {
          <div class="signal-grid">
            <div class="signal-cell">
              <span class="signal-cell__label">Tendencia</span>
              <span class="signal-cell__value" [class.text--ok]="s.trend === 'bullish'"
                                              [class.text--loss]="s.trend === 'bearish'">
                {{ trendLabel(s.trend) }}
              </span>
            </div>
            <div class="signal-cell">
              <span class="signal-cell__label">Score</span>
              <div class="score-track" [class.score-track--neg]="s.score < 0">
                <div class="score-fill" [style.width.%]="scoreWidth(s.score)"></div>
              </div>
              <span class="signal-cell__value">{{ s.score | num:2 }}</span>
            </div>
            <div class="signal-cell">
              <span class="signal-cell__label">RSI 14</span>
              <span class="signal-cell__value" [class.text--warn]="s.indicators.rsi14 != null && s.indicators.rsi14 >= s.indicators.rsi_overbought"
                                              [class.text--ok]="s.indicators.rsi14 != null && s.indicators.rsi14 <= s.indicators.rsi_oversold">
                {{ s.indicators.rsi14 != null ? (s.indicators.rsi14 | num:1) : '—' }}
              </span>
            </div>
            <div class="signal-cell">
              <span class="signal-cell__label">MACD hist</span>
              <span class="signal-cell__value" [class.text--ok]="(s.indicators.macd_hist ?? 0) >= 0"
                                              [class.text--loss]="(s.indicators.macd_hist ?? 0) < 0">
                {{ s.indicators.macd_hist != null ? (s.indicators.macd_hist | num:2) : '—' }}
              </span>
            </div>
            @if (s.market_type === 'FUTURES') {
              <div class="signal-cell">
                <span class="signal-cell__label">Funding rate</span>
                <span class="signal-cell__value">{{ s.funding_rate != null ? (s.funding_rate | pct) : '—' }}</span>
              </div>
            }
            <div class="signal-cell">
              <span class="signal-cell__label">Cambio 24h</span>
              <span class="signal-cell__value" [class.text--ok]="(s.change_24h_pct ?? 0) >= 0"
                                              [class.text--loss]="(s.change_24h_pct ?? 0) < 0">
                {{ s.change_24h_pct != null ? (s.change_24h_pct | num:2) : '—' }}%
              </span>
            </div>
            <div class="signal-cell">
              <span class="signal-cell__label">Confianza</span>
              <span class="signal-cell__value">{{ s.confidence_pct }}%</span>
            </div>
          </div>
          <p class="signal-summary">{{ s.summary }}</p>
        } @else if (signalError(); as err) {
          <p class="empty">⚠️ No se pudo obtener la señal de mercado:<br />{{ err }}</p>
        } @else {
          <p class="empty">Calculando señal de mercado…</p>
        }
      </section>

      <!-- Cuenta (spot o futuros) -->
      <section class="card section">
        <header class="card__header">
          <h2>Cuenta {{ marketType() === 'FUTURES' ? 'futuros' : 'spot' }} — {{ testMode() ? 'Testnet' : 'Producción' }}</h2>
          @if (balance()?.market_type === 'FUTURES') {
            <span class="badge badge--futures">Apalancamiento {{ balance()?.leverage ?? 1 }}×</span>
          }
        </header>
        @if (balance(); as b) {
          @if (b.market_type === 'FUTURES') {
            @if (b.positions.length > 0) {
              <div class="positions">
                @for (pos of b.positions; track pos.symbol) {
                  <div class="pos-card" [class.pos-card--long]="pos.side === 'LONG'"
                                       [class.pos-card--short]="pos.side === 'SHORT'">
                    <div class="pos-card__top">
                      <span class="badge" [class.badge--ok]="pos.side === 'LONG'"
                                         [class.badge--danger]="pos.side === 'SHORT'">{{ pos.side }}</span>
                      <span class="pos-card__sym">{{ pos.symbol }}</span>
                      <span class="pos-card__pnl" [class.text--ok]="pos.unrealized_profit >= 0"
                                                 [class.text--loss]="pos.unrealized_profit < 0">
                        {{ pos.unrealized_profit | usdt }}
                      </span>
                    </div>
                    <dl class="pos-card__grid">
                      <dt>Entrada</dt><dd>{{ pos.entry_price | num:2 }}</dd>
                      <dt>Mark</dt><dd>{{ pos.mark_price | num:2 }}</dd>
                      <dt>Cantidad</dt><dd>{{ pos.position_amt | num }}</dd>
                      <dt>Nocional</dt><dd>{{ pos.notional | usdt }}</dd>
                      <dt>Liquidación</dt><dd>{{ pos.liquidation_price != null ? (pos.liquidation_price | num:2) : '—' }}</dd>
                      <dt>Apalanc.</dt><dd>{{ pos.leverage }}×</dd>
                      <dt>Margen</dt><dd>{{ pos.margin_type }}</dd>
                      <dt>PnL %</dt><dd [class.text--ok]="pos.profit_pct >= 0" [class.text--loss]="pos.profit_pct < 0">{{ pos.profit_pct | num:2 }}%</dd>
                    </dl>
                  </div>
                }
              </div>
            } @else {
              <p class="empty">No hay posiciones abiertas en futuros.</p>
            }
            <div class="balance-grid">
              @for (asset of mainAssets(b); track asset.asset) {
                <div class="stat-card">
                  <span class="stat-card__label">{{ asset.asset }}</span>
                  <span class="stat-card__value stat-card__value--small">{{ asset.free | num }}</span>
                </div>
              }
            </div>
          } @else {
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
          }
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
            {{ stats()?.total_profit != null ? (stats()?.total_profit! | usdt) : '—' }}
          </span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Win rate</span>
          <span class="stat-card__value">{{ winRate() | pct }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-card__label">Spot / Futuros</span>
          <span class="stat-card__value stat-card__value--small">
            {{ stats()?.total_spot ?? 0 }} / {{ stats()?.total_futures ?? 0 }}
          </span>
        </div>
      </section>

      <!-- Últimas transacciones -->
      <section class="card section">
        <header class="card__header">
          <h2>Últimas transacciones</h2>
          <a class="link" routerLink="/transactions">Ver todas →</a>
        </header>
        <div class="table-wrap">
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
                <tr><td colspan="12" class="empty">Sin transacciones todavía.</td></tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .muted { color: var(--muted); font-weight: 400; font-size: 0.85rem; }
    .section { margin-bottom: 1.5rem; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; }
    .page__subtitle { color: var(--muted); margin: 0.25rem 0 0; }
    .header__actions { display: flex; align-items: center; gap: 0.75rem; }
    .sse-badge { font-size: 0.78rem; color: var(--muted); }
    .sse-badge--on { color: var(--ok); }
    .sse-badge--off { color: var(--warn); }
    .card__header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.2rem; border-bottom: 1px solid var(--border); }
    .card__header h2 { font-size: 1.05rem; margin: 0; }
    .badge { padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.03em; }
    .badge--ok { background: var(--ok-bg); color: var(--ok); }
    .badge--danger { background: var(--danger-bg); color: var(--danger); }
    .badge--neutral { background: var(--warn-bg); color: var(--warn); }
    .badge--futures { background: rgba(168, 85, 247, 0.15); color: #a78bfa; }
    .badge--signal { font-size: 0.85rem; padding: 0.3rem 0.9rem; }
    .link { color: var(--accent); text-decoration: none; font-size: 0.9rem; }
    .empty { text-align: center; color: var(--muted); padding: 2rem !important; margin: 0; }
    .signal-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; padding: 1rem 1.2rem; }
    .signal-cell { display: flex; flex-direction: column; gap: 0.35rem; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 0.7rem 0.9rem; }
    .signal-cell__label { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .signal-cell__value { font-size: 1rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .score-track { height: 8px; border-radius: 999px; background: var(--danger-bg); overflow: hidden; position: relative; }
    .score-track--neg .score-fill { background: var(--danger); margin-left: auto; }
    .score-fill { height: 100%; border-radius: 999px; background: var(--ok); transition: width 0.4s; }
    .signal-summary { padding: 0 1.2rem 1rem; margin: 0; color: var(--muted); font-size: 0.88rem; }
    .positions { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem; padding: 1rem 1.2rem; }
    .pos-card { border: 1px solid var(--border); border-radius: 12px; padding: 0.9rem 1rem; background: var(--bg); }
    .pos-card--long { border-left: 3px solid var(--ok); }
    .pos-card--short { border-left: 3px solid var(--danger); }
    .pos-card__top { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.75rem; }
    .pos-card__sym { font-weight: 800; flex: 1; }
    .pos-card__pnl { font-weight: 800; font-variant-numeric: tabular-nums; }
    .pos-card__grid { display: grid; grid-template-columns: auto 1fr; gap: 0.35rem 0.9rem; margin: 0; font-size: 0.85rem; }
    .pos-card__grid dt { color: var(--muted); }
    .pos-card__grid dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
    .balance-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; padding: 1rem 1.2rem; }
    .stat-card { display: flex; flex-direction: column; gap: 0.35rem; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 0.9rem 1rem; }
    .stat-card__label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-card__value { font-size: 1.35rem; font-weight: 800; font-variant-numeric: tabular-nums; }
    .stat-card__value--small { font-size: 1rem; }
    .chips { display: flex; flex-wrap: wrap; gap: 0.3rem; }
    .chip { background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 0.15rem 0.5rem; font-size: 0.75rem; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }
    .text--ok { color: var(--ok); }
    .text--warn { color: var(--warn); }
    .text--loss { color: var(--danger); }
    .th--num { text-align: right; }
  `],
})
export class DashboardComponent {
  private readonly transactionService = inject(TransactionService);
  private readonly balanceService = inject(BalanceService);
  private readonly environmentService = inject(EnvironmentService);
  private readonly eventService = inject(EventService);
  private readonly analysisService = inject(AnalysisService);
  private readonly marketSignalService = inject(MarketSignalService);
  private readonly reloadTrigger = signal(0);

  /** Ambiente seleccionado en el switch del sidebar (true=Testnet). */
  protected readonly testMode = this.environmentService.testMode$;

  /** Mercado seleccionado (SPOT | FUTURES). */
  protected readonly marketType = this.environmentService.marketType$;

  /** Estado de la conexión SSE (null mientras conecta, true/false después). */
  protected readonly sseConnected = toSignal(this.eventService.connection$);

  /** Señal de mercado en vivo (vía SSE) con fallback HTTP al arrancar. */
  private readonly fetchedSignal = toSignal(
    combineLatest([toObservable(this.testMode), toObservable(this.marketType), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode, marketType]) => {
        this.signalError.set(null);
        return this.analysisService.getSignal(testMode, marketType).pipe(
          catchError((err) => {
            const detail = err?.error?.detail ?? err?.message ?? 'error desconocido';
            this.signalError.set(detail);
            return of(null);
          }),
        );
      }),
    ),
  );
  protected readonly signal = computed<MarketAnalysis | undefined>(
    () => this.marketSignalService.signalFor(this.testMode(), this.marketType()) ?? this.fetchedSignal() ?? undefined,
  );
  protected readonly signalError = signal<string | null>(null);

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
    combineLatest([toObservable(this.testMode), toObservable(this.marketType), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode, marketType]) =>
        this.transactionService.list({ testMode, marketType, limit: 10 }),
      ),
    ),
  );
  protected readonly balance = toSignal(
    combineLatest([toObservable(this.testMode), toObservable(this.marketType), toObservable(this.reloadTrigger)]).pipe(
      switchMap(([testMode, marketType]) => {
        this.balanceError.set(null);
        return this.balanceService.get(testMode, marketType).pipe(
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

  trendLabel(trend: string): string {
    return trend === 'bullish' ? '▲ Alcista' : trend === 'bearish' ? '▼ Bajista' : '◆ Neutral';
  }

  /** Anchura de la barra de score (0..100%). */
  scoreWidth(score: number): number {
    return Math.min(100, Math.max(0, Math.abs(score) / 6 * 100));
  }

  winRate(): number {
    const stats = this.stats();
    if (!stats || stats.closed === 0) return 0;
    const wins = stats.wins_test + stats.wins_real;
    return wins / stats.closed * 100;
  }

  refresh(): void {
    this.reloadTrigger.update((n) => n + 1);
  }
}


