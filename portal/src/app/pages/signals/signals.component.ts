import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { WebsocketService } from '../../websocket.service';
import { interval, Subscription } from 'rxjs';
import { ConfirmationModalComponent } from '../../components/confirmation-modal';

declare var Chart: any;

@Component({
  selector: 'app-signals',
  standalone: true,
  imports: [CommonModule, ConfirmationModalComponent],
  template: `
<div class="page-wrapper">
  <header class="page-header">
    <div class="header-brand">
      <h1 class="gradient-text">Signal <span style="font-weight:300;opacity:.8">Monitor</span></h1>
      <p>Historial de indicadores tecnicos en tiempo real - {{ activeSymbol }}</p>
    </div>
    <div class="header-actions">
      <button (click)="go('/')" class="btn-secondary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;">Dashboard</button>
      <button (click)="go('/performance')" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;background:linear-gradient(135deg,#10b981,#3b82f6);border:none;">Analytics</button>
    </div>
  </header>

  <!-- Live indicator pills -->
  <div class="metrics-bar" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr));">
    <div class="glass-card" style="padding:.75rem;text-align:center;border-color:rgba(0,210,255,0.3);">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">PRECIO ACTUAL</div>
      <div style="font-size:1.4rem;font-weight:900;" [style.color]="priceVsEmaColor">$ {{ live?.price | number:'1.2-2' }}</div>
      <div style="font-size:.6rem;font-weight:700;" [style.color]="priceVsEmaColor">{{ priceVsEma }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">RSI (14)</div>
      <div style="font-size:1.8rem;font-weight:900;" [style.color]="rsiColor">{{ live?.rsi | number:'1.1-1' }}</div>
      <div style="font-size:.6rem;font-weight:700;" [style.color]="rsiColor">{{ rsiLabel }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">ADX (14)</div>
      <div style="font-size:1.8rem;font-weight:900;" [style.color]="live?.adx>25?'#f59e0b':'var(--text-muted)'">{{ live?.adx | number:'1.1-1' }}</div>
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;">{{ live?.adx>35?'STRONG TREND':(live?.adx>25?'TRENDING':'RANGING') }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">EMA 200</div>
      <div style="font-size:1.3rem;font-weight:900;color:#fff;">$ {{ live?.ema_slow | number:'1.2-2' }}</div>
      <div style="font-size:.6rem;font-weight:700;" [style.color]="priceVsEmaColor">{{ priceVsEma }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">EMA 50 ⚡ ACTIVO</div>
      <div style="font-size:1.3rem;font-weight:900;" [style.color]="priceVsEmaColor">$ {{ live?.ema_fast | number:'1.2-2' }}</div>
      <div style="font-size:.6rem;font-weight:700;" [style.color]="priceVsEmaColor">{{ priceVsEma }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">VOLUME</div>
      <div style="font-size:1.8rem;font-weight:900;" [style.color]="live?.volume_ratio>=1.2?'var(--success)':'var(--text-muted)'">
        {{ live?.volume_ratio | number:'1.2-2' }}x
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;">{{ live?.volume_ratio >= 1.2 ? 'HIGH VOL' : (live?.volume_ratio >= 1.0 ? 'NORMAL' : 'LOW VOL') }}</div>
    </div>
    <div class="glass-card" style="padding:.75rem;text-align:center;">
      <div style="font-size:.55rem;color:var(--text-muted);font-weight:700;margin-bottom:.25rem;">ATR (14)</div>
      <div style="font-size:1.8rem;font-weight:900;color:var(--primary);">$ {{ live?.atr | number:'1.3-3' }}</div>
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;">Volatilidad 1h</div>
    </div>
  </div>

  <!-- Signal readiness widget -->
  <div class="glass-card" style="margin-top:0;padding:1.25rem;">
    <h3 style="color:var(--text-muted);margin:0 0 1rem;font-size:.9rem;text-transform:uppercase;letter-spacing:1px;">Condiciones de Entrada - Estado Actual</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.75rem;">
      <div *ngFor="let cond of conditions" class="tooltip-container"
           [style.background]="cond.ok?'rgba(16,185,129,0.06)':'rgba(239,68,68,0.05)'"
           style="border:1px solid rgba(255,255,255,0.06);border-radius:.6rem;padding:.75rem;display:flex;align-items:center;gap:.75rem;cursor:help;">
        <div class="tooltip-text">{{ cond.tooltip }}</div>
        <div style="width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0;"
             [style.background]="cond.ok?'rgba(16,185,129,0.2)':'rgba(239,68,68,0.15)'"
             [style.color]="cond.ok?'var(--success)':'var(--danger)'">
          {{ cond.ok ? 'OK' : 'X' }}
        </div>
        <div>
          <div style="font-size:.7rem;font-weight:700;color:#fff;">{{ cond.label }}</div>
          <div style="font-size:.6rem;color:var(--text-muted);">{{ cond.detail }}</div>
        </div>
      </div>
    </div>
    <div style="margin-top:1rem;text-align:center;">
      <div [style.background]="allConditionsMet?'rgba(16,185,129,0.1)':'rgba(245,158,11,0.08)'"
           style="display:inline-flex;align-items:center;gap:.5rem;padding:.5rem 1.5rem;border-radius:100px;border:1px solid rgba(255,255,255,0.1);">
        <div style="width:8px;height:8px;border-radius:50%;"
             [style.background]="allConditionsMet?'var(--success)':'#f59e0b'"
             [style.box-shadow]="'0 0 8px ' + (allConditionsMet?'var(--success)':'#f59e0b')"></div>
        <span style="font-size:.75rem;font-weight:800;"
              [style.color]="allConditionsMet?'var(--success)':'#f59e0b'">
          {{ allConditionsMet ? 'LISTO PARA ENTRADA' : 'ESPERANDO CONDICIONES (' + conditionsMet + '/4)' }}
        </span>
      </div>
    </div>
  </div>

  <!-- IA Prediction Card -->
  <div class="glass-card" style="margin-top:1rem;padding:1.25rem;display:flex;justify-content:space-between;align-items:center;">
    <div>
      <h3 style="color:var(--text-muted);margin:0 0 0.25rem;font-size:.9rem;text-transform:uppercase;letter-spacing:1px;">IA Predictor Local (KNN)</h3>
      <p style="color:var(--text-muted);font-size:.7rem;margin:0;">Entrena con el 50% de los datos y predice con el resto.</p>
    </div>
    <div style="display:flex;align-items:center;gap:1rem;">
      <div *ngIf="aiPrediction" style="text-align:right;">
        <div style="font-size:1.2rem;font-weight:900;color:#fff;">{{ aiPrediction }}</div>
        <div style="font-size:.6rem;color:var(--text-muted);">Precisión: {{ aiAccuracy | percent:'1.1-1' }}</div>
        <div *ngIf="aiRecommendedRsi" style="font-size:.6rem;color:#fbbf24;font-weight:700;">RSI Sugerido: {{ aiRecommendedRsi }}</div>
      </div>
      <button (click)="consultarIA()" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;" [disabled]="aiLoading">
        {{ aiLoading ? 'Procesando...' : 'Consultar IA' }}
      </button>
    </div>
  </div>

  <!-- Manual Control Card -->
  <div class="glass-card" style="margin-top:1rem;padding:1.25rem;display:flex;justify-content:space-between;align-items:center;">
    <div>
      <h3 style="color:var(--text-muted);margin:0 0 0.25rem;font-size:.9rem;text-transform:uppercase;letter-spacing:1px;">Control Manual</h3>
      <p style="color:var(--text-muted);font-size:.7rem;margin:0;">Fuerza una entrada omitiendo las reglas del bot.</p>
    </div>
    <div style="display:flex;align-items:center;gap:1rem;">
      <button (click)="forceTradeAction('BUY')" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;background:linear-gradient(135deg,#10b981,#059669);border:none;">
        Forzar LONG
      </button>
      <button (click)="forceTradeAction('SELL')" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;background:linear-gradient(135deg,#ef4444,#dc2626);border:none;">
        Forzar SHORT
      </button>
    </div>
  </div>

  <app-confirmation-modal 
    *ngIf="showModal" 
    [message]="modalMessage" 
    [symbol]="pendingTradeData?.symbol"
    [side]="pendingTradeData?.side"
    [livePrice]="live?.price"
    [sl]="modalSl"
    [tp]="modalTp"
    [quantity]="pendingTradeData?.quantity"
    [confirmColor]="modalConfirmColor" 
    (close)="showModal=false" 
    (confirm)="executeForcedTrade($event)">
  </app-confirmation-modal>

  <!-- RSI + Price Chart -->
  <div class="glass-card" style="margin-top:1.5rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:.5rem;">
      <h3 style="color:var(--text-muted);margin:0;font-size:1rem;">RSI + Precio - Ultimas {{ logs.length }} lecturas (1h)</h3>
      <div style="display:flex;gap:.75rem;font-size:.65rem;font-weight:700;">
        <span style="color:var(--primary);">* Precio</span>
        <span style="color:#fbbf24;">* RSI</span>
        <span style="color:rgba(16,185,129,0.7);">--- RSI {{ currentRsiThreshold }} (entrada)</span>
      </div>
    </div>
    <div style="height:320px;position:relative;"><canvas id="signalChart"></canvas></div>
  </div>

  <!-- ADX + Volume Chart -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.5rem;" class="responsive-grid-2">
    <div class="glass-card">
      <h3 style="color:var(--text-muted);margin:0 0 1rem;font-size:1rem;">ADX - Fuerza de Tendencia</h3>
      <div style="height:200px;position:relative;"><canvas id="adxChart"></canvas></div>
    </div>
    <div class="glass-card">
      <h3 style="color:var(--text-muted);margin:0 0 1rem;font-size:1rem;">Volumen Ratio</h3>
      <div style="height:200px;position:relative;"><canvas id="volChart"></canvas></div>
    </div>
  </div>
</div>
  `,
  styles: [`
    .tooltip-container {
      position: relative;
    }
    .tooltip-container:hover .tooltip-text {
      visibility: visible;
      opacity: 1;
    }
    .tooltip-text {
      visibility: hidden;
      width: 220px;
      background: rgba(15, 23, 42, 0.95);
      color: #e2e8f0;
      text-align: left;
      border-radius: 0.5rem;
      padding: 0.75rem;
      position: absolute;
      z-index: 1000;
      bottom: 110%;
      left: 50%;
      transform: translateX(-50%);
      opacity: 0;
      transition: opacity 0.2s ease, visibility 0.2s;
      border: 1px solid rgba(255, 255, 255, 0.1);
      font-size: 0.75rem;
      pointer-events: none;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(4px);
      line-height: 1.4;
    }
    .tooltip-text::after {
      content: "";
      position: absolute;
      top: 100%;
      left: 50%;
      margin-left: -5px;
      border-width: 5px;
      border-style: solid;
      border-color: rgba(15, 23, 42, 0.95) transparent transparent transparent;
    }
  `]
})
export class SignalsComponent implements OnInit, OnDestroy, AfterViewInit {
  logs: any[]  = [];
  live: any    = null;
  aiPrediction: string = '';
  aiAccuracy: number = 0;
  aiRecommendedRsi: number | null = null;
  aiLoading: boolean = false;

  // Modal properties
  showModal: boolean = false;
  modalMessage: string = '';
  modalSl: number = 0;
  modalTp: number = 0;
  modalConfirmColor: string = '';
  pendingTradeData: any = null;

  get activeSymbol(): string {
    return this.live?.symbol || 'CRYPTO';
  }

  private signalChart: any;
  private adxChart: any;
  private volChart: any;
  private sub?: Subscription;

  constructor(private api: ApiService, private wsService: WebsocketService, private router: Router, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.fetchLogs();
    this.sub = this.wsService.getMessages().subscribe(msg => {
      if (msg.type === 'PRICE_UPDATE') {
        const data = msg.data;
        const newLog = {
          symbol: data.symbol,
          price: parseFloat(data.price),
          rsi: parseFloat(data.rsi),
          rsi_oversold:  parseFloat(data.rsi_oversold  || '35'),
          rsi_overbought: parseFloat(data.rsi_overbought || '68'),
          rsi_prev: parseFloat(data.rsi_prev || '50'),
          ema_slow: parseFloat(data.ema200 || '0'),
          ema_fast: parseFloat(data.ema_fast || '0'),
          adx: parseFloat(data.adx || '0'),
          plus_di: parseFloat(data.plus_di || '0'),
          minus_di: parseFloat(data.minus_di || '0'),
          volume_ratio: parseFloat(data.volume_ratio || '0'),
          atr: parseFloat(data.atr || '0'),
          timestamp: data.timestamp || new Date().toISOString()
        };
        this.logs.push(newLog);
        if (this.logs.length > 100) this.logs.shift();
        this.live = newLog;
        
        // Actualizar SL y TP en tiempo real si el modal está abierto
        if (this.showModal && this.pendingTradeData) {
          const price = newLog.price;
          const atr = newLog.atr;
          if (price && atr) {
            if (this.pendingTradeData.side === 'BUY') {
              this.modalSl = parseFloat((price - (atr * 1.1)).toFixed(3));
              this.modalTp = parseFloat((price + (atr * 1.2)).toFixed(3));
            } else {
              this.modalSl = parseFloat((price + (atr * 1.1)).toFixed(3));
              this.modalTp = parseFloat((price - (atr * 1.2)).toFixed(3));
            }
          }
        }
        
        this.cdr.detectChanges();
        this.initCharts();
      }
    });
  }

  ngAfterViewInit() {}
  ngOnDestroy() { this.sub?.unsubscribe(); }

  go(path: string) { this.router.navigate([path]); }

  fetchLogs() {
    this.api.getPriceLogs(0, 100).subscribe({
      next: (res: any) => {
        this.logs = (res.logs || []).reverse(); // Cronológico
        this.live = this.logs[this.logs.length - 1] || null;
        this.cdr.detectChanges();
        this.initCharts();
      }
    });
  }

  consultarIA() {
    this.aiLoading = true;
    this.api.getLocalAiPrediction().subscribe({
      next: (res: any) => {
        this.aiPrediction = res.prediction;
        this.aiAccuracy = res.model_accuracy;
        this.aiRecommendedRsi = res.recommended_rsi;
        this.aiLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error(err);
        this.aiLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  forceTradeAction(side: string) {
    const price = parseFloat(this.live?.price);
    const atr = parseFloat(this.live?.atr);
    const symbol = this.live?.symbol || 'SOLUSDT';
    
    if (!price || !atr) {
      alert('Faltan datos de precio o ATR para calcular SL/TP');
      return;
    }
    
    const slMult = 1.1;
    const tpMult = 1.2;
    
    let sl = 0;
    let tp = 0;
    
    if (side === 'BUY') {
      sl = parseFloat((price - (atr * slMult)).toFixed(3));
      tp = parseFloat((price + (atr * tpMult)).toFixed(3));
    } else {
      sl = parseFloat((price + (atr * slMult)).toFixed(3));
      tp = parseFloat((price - (atr * tpMult)).toFixed(3));
    }
    
    const quantity = 0.1; // Cantidad por defecto
    
    this.pendingTradeData = { symbol, side, quantity };
    this.modalSl = sl;
    this.modalTp = tp;
    
    this.modalMessage = `¿Estás seguro de que deseas forzar una operación en ${side === 'BUY' ? 'LONG' : 'SHORT'}?`;
    this.modalConfirmColor = side === 'BUY' ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#ef4444,#dc2626)';
    this.showModal = true;
  }

  executeForcedTrade(event: {sl: number, tp: number, quantity: number}) {
    if (!this.pendingTradeData) return;
    
    this.showModal = false;
    
    const tradeData = {
      symbol: this.pendingTradeData.symbol,
      side: this.pendingTradeData.side,
      quantity: event.quantity,
      sl: event.sl,
      tp: event.tp
    };
    
    this.api.forceTrade(tradeData).subscribe({
      next: (res: any) => {
        alert(`Orden forzada con éxito: ${tradeData.side}\nCant: ${tradeData.quantity}\nSL: ${tradeData.sl.toFixed(2)}\nTP: ${tradeData.tp.toFixed(2)}`);
        this.pendingTradeData = null;
      },
      error: (err) => {
        console.error(err);
        alert('Error al forzar orden');
        this.pendingTradeData = null;
      }
    });
  }

  get rsiColor(): string {
    const r = parseFloat(this.live?.rsi) || 50;
    return r < 30 ? 'var(--success)' : r > 68 ? 'var(--danger)' : 'var(--text-muted)';
  }

  get rsiLabel(): string {
    const r = parseFloat(this.live?.rsi) || 50;
    return r < 30 ? 'OVERSOLD' : r > 68 ? 'OVERBOUGHT' : 'NEUTRAL';
  }

  get priceVsEma(): string {
    const p = parseFloat(this.live?.price);  const e = parseFloat(this.live?.ema_fast);
    if (!p || !e) return '---';
    return p > e ? 'ABOVE EMA50' : 'BELOW EMA50';
  }

  get priceVsEmaColor(): string {
    const p = parseFloat(this.live?.price);  const e = parseFloat(this.live?.ema_fast);
    if (!p || !e) return 'var(--text-muted)';
    return p > e ? 'var(--success)' : 'var(--danger)';
  }

  get dynamicThresholds(): { long: number, short: number } {
    // Leer del WebSocket en tiempo real (el bot envía los umbrales activos del .env)
    const rsiOversold   = parseFloat(this.live?.rsi_oversold)  || 35.0;
    const rsiOverbought = parseFloat(this.live?.rsi_overbought) || 68.0;
    return { long: rsiOversold, short: rsiOverbought };
  }

  get currentRsiThreshold(): number {
    const thresholds = this.dynamicThresholds;
    const rsi = parseFloat(this.live?.rsi) || 50;
    return rsi > 50 ? thresholds.short : thresholds.long;
  }

  get conditions(): { label: string; detail: string; ok: boolean; tooltip: string }[] {
    const rsi     = parseFloat(this.live?.rsi)          || 50;
    const adx     = parseFloat(this.live?.adx)          || 0;
    const price   = parseFloat(this.live?.price)         || 0;
    const emaSlow = parseFloat(this.live?.ema_slow)      || 0;
    const vol     = parseFloat(this.live?.volume_ratio)  || 0;
    const plusDi  = parseFloat(this.live?.plus_di)       || 0;
    const minusDi = parseFloat(this.live?.minus_di)      || 0;

    const lookingForShort = rsi > 50;
    const thresholds = this.dynamicThresholds;
    
    // 1. RSI
    const umbralLong = thresholds.long;
    const umbralShort = thresholds.short;
    
    const isRsiOk = lookingForShort ? (rsi > umbralShort) : (rsi < umbralLong);
    const rsiDetail = lookingForShort 
        ? `RSI ${rsi.toFixed(1)} > ${umbralShort.toFixed(1)} (Short)` 
        : `RSI ${rsi.toFixed(1)} < ${umbralLong.toFixed(1)} (Long)`;

    // 2. Contexto
    let isContextOk = false;
    let contextDetail = '';
    const contextLabel = lookingForShort ? 'Giro Bajista' : 'Contexto Alcista';
    
    if (lookingForShort) {
        // Top-catching short: basta presión vendedora OR RSI cayendo (igual que la estrategia)
        const rsiPrev = parseFloat(this.live?.rsi_prev) || parseFloat(this.logs.length > 1 ? this.logs[this.logs.length - 2]?.rsi : rsi) || 50;
        const bearishPressure = minusDi >= plusDi;
        const rsiFalling      = rsi < rsiPrev;
        const momentumAgotado = bearishPressure || rsiFalling;
        isContextOk = momentumAgotado;
        contextDetail = momentumAgotado
          ? (bearishPressure ? 'RSI cayendo y presión vendedora (DI- >= DI+)' : 'RSI girando a la baja')
          : 'Esperando DI- >= DI+ o RSI cayendo';
    } else {
        // EMA50 activa: el precio debe estar sobre la EMA50 para abrir LONG
        const emaFast = parseFloat(this.live?.ema_fast) || 0;
        isContextOk = emaFast > 0 && price > emaFast;
        const diff = emaFast > 0 ? (price - emaFast).toFixed(2) : '?';
        contextDetail = isContextOk
          ? `Precio $${price.toFixed(2)} sobre EMA50 $${emaFast.toFixed(2)} (+$${diff})`
          : `Precio $${price.toFixed(2)} bajo EMA50 $${emaFast.toFixed(2)} ($${diff})`;
    }

    // 3. Tendencia
    let isTrendOk = false;
    let trendDetail = '';
    const trendLabel = lookingForShort ? 'Sin Tendencia Alcista Fuerte' : 'Sin Tendencia Bajista Fuerte';
    if (lookingForShort) {
      const isUptrendHard = adx > 45 && plusDi > minusDi;
      isTrendOk = !isUptrendHard;
      trendDetail = isUptrendHard ? 'Tendencia alcista extrema detectada (ADX > 45)' : 'Sin tendencia alcista extrema';
    } else {
      const isDowntrendHard = adx > 45 && minusDi > plusDi;
      isTrendOk = !isDowntrendHard;
      trendDetail = isDowntrendHard ? 'Tendencia bajista extrema detectada (ADX > 45)' : 'Sin tendencia bajista extrema';
    }

    // 4. Volumen
    const isVolOk = vol >= 1.0;
    const volDetail = `${vol.toFixed(2)}x del promedio >= 1.0x`;

    return [
      { 
        label: `RSI (${lookingForShort ? 'Short' : 'Long'})`, 
        detail: rsiDetail, 
        ok: isRsiOk,
        tooltip: 'El Índice de Fuerza Relativa (RSI) mide la velocidad y el cambio de los movimientos de precios para identificar condiciones de sobrecompra o sobreventa.'
      },
      { 
        label: contextLabel, 
        detail: contextDetail, 
        ok: isContextOk,
        tooltip: lookingForShort 
          ? 'Valida el agotamiento del momentum alcista. Requiere que el RSI esté cayendo y que los indicadores direccionales favorezcan a los osos.'
          : 'Filtro EMA50 activo: el precio debe estar por encima de la EMA de 50 períodos para confirmar micro-tendencia alcista y habilitar la entrada LONG.'
      },
      { 
        label: trendLabel, 
        detail: trendDetail, 
        ok: isTrendOk,
        tooltip: 'Mide la fuerza de la tendencia mediante el ADX. Si la tendencia en contra es demasiado fuerte (ADX > 45), se bloquea la operación por seguridad.'
      },
      // Volumen — solo informativo, no bloquea entrada
      { 
        label: 'Volumen', 
        detail: `${vol.toFixed(2)}x del promedio (informativo)`, 
        ok: true,
        tooltip: 'El volumen se muestra como información adicional pero no bloquea la entrada.'
      }
    ];
  }
  
  getHistoricalRsiThreshold(adxValue: number): number {
    const baseRsi = this.activeSymbol.includes('BTC') ? 65 : 30;
    if (adxValue >= 25) {
      return Math.max(baseRsi - 5, 20);
    } else if (adxValue < 20) {
      return Math.min(baseRsi + 5, 40);
    }
    return baseRsi;
  }
  get conditionsMet(): number { return this.conditions.filter(c => c.ok).length; }
  get allConditionsMet(): boolean { return this.conditionsMet >= 3; }

  private initCharts() {
    this.buildSignalChart();
    this.buildAdxChart();
    this.buildVolChart();
  }

  private buildSignalChart() {
    const ctx = document.getElementById('signalChart') as HTMLCanvasElement;
    if (!ctx || this.logs.length === 0) return;
    if (this.signalChart) this.signalChart.destroy();

    const labels = this.logs.map(l => new Date(l.timestamp).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }));

    this.signalChart = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          { type: 'line', label: 'Precio', data: this.logs.map(l => parseFloat(l.price)),
            borderColor: '#00d2ff', backgroundColor: 'rgba(0,210,255,0.05)',
            borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3, yAxisID: 'yPrice' },
          { type: 'line', label: 'RSI', data: this.logs.map(l => parseFloat(l.rsi)),
            borderColor: '#fbbf24', borderWidth: 2, pointRadius: 0, fill: false, tension: 0.3, yAxisID: 'yRsi' },
          { type: 'line', label: 'Umbral RSI', data: this.logs.map(l => this.getHistoricalRsiThreshold(parseFloat(l.adx||0))),
            borderColor: 'rgba(16,185,129,0.5)', borderDash: [4, 4], borderWidth: 1.5,
            pointRadius: 0, fill: false, yAxisID: 'yRsi' },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: '#9ca3af', font: { size: 9 }, maxTicksLimit: 12 }, grid: { color: 'rgba(255,255,255,0.03)' } },
          yPrice: { position: 'left',  ticks: { color: '#00d2ff', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
          yRsi:   { position: 'right', min: 0, max: 100, ticks: { color: '#fbbf24', font: { size: 9 } }, grid: { display: false } }
        },
        plugins: { legend: { labels: { color: '#9ca3af', font: { size: 10 } } } }
      }
    });
  }

  private buildAdxChart() {
    const ctx = document.getElementById('adxChart') as HTMLCanvasElement;
    if (!ctx || this.logs.length === 0) return;
    if (this.adxChart) this.adxChart.destroy();
    const labels = this.logs.map(l => new Date(l.timestamp).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }));
    this.adxChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'ADX', data: this.logs.map(l => parseFloat(l.adx||0)),
            borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)',
            borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3 },
          { label: 'Umbral 25', data: this.logs.map(() => 25),
            borderColor: 'rgba(255,255,255,0.2)', borderDash: [4,4], borderWidth: 1, pointRadius: 0, fill: false }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: '#9ca3af', font: { size: 9 }, maxTicksLimit: 8 }, grid: { display: false } },
          y: { min: 0, ticks: { color: '#9ca3af', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
        },
        plugins: { legend: { labels: { color: '#9ca3af', font: { size: 9 } } } }
      }
    });
  }

  private buildVolChart() {
    const ctx = document.getElementById('volChart') as HTMLCanvasElement;
    if (!ctx || this.logs.length === 0) return;
    if (this.volChart) this.volChart.destroy();
    const labels  = this.logs.map(l => new Date(l.timestamp).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }));
    const volData = this.logs.map(l => parseFloat(l.volume_ratio||0));
    const bgColors = volData.map(v => v >= 1.2 ? 'rgba(16,185,129,0.7)' : 'rgba(100,116,139,0.4)');

    this.volChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Vol Ratio', data: volData, backgroundColor: bgColors, borderRadius: 3, borderSkipped: false },
          { type: 'line', label: 'Umbral 1.0x', data: this.logs.map(() => 1.0),
            borderColor: 'rgba(255,255,255,0.3)', borderDash: [4,4], borderWidth: 1, pointRadius: 0, fill: false }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: '#9ca3af', font: { size: 9 }, maxTicksLimit: 8 }, grid: { display: false } },
          y: { min: 0, ticks: { color: '#9ca3af', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
        },
        plugins: { legend: { labels: { color: '#9ca3af', font: { size: 9 } } } }
      }
    });
  }
}
