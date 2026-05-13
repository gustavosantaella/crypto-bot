import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { WebsocketService } from '../../websocket.service';
import { interval, Subscription } from 'rxjs';
import { MetricCard } from '../../components/metric-card';
import { AssetCard } from '../../components/asset-card';
import { AiModalComponent } from '../../components/ai-modal';

declare var Chart: any;

interface Trade {
  id: number;
  timestamp: string;
  symbol: string;
  side: string;
  trade_type: string;
  price: any;
  quantity: any;
  target_tp?: any;
  target_sl?: any;
  pnl?: any;
  balance_before?: any;
  message?: string;
}

interface PriceLog {
  symbol: string;
  price: number;
  rsi: number;
  timestamp: string;
}

interface Balance {
  asset: string;
  free: number;
  locked: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MetricCard, AssetCard, AiModalComponent],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  status: any = { has_position: false, last_buy_price: 0 };
  trades: Trade[] = [];
  priceLogs: PriceLog[] = [];
  balances: Balance[] = [];
  totalPnL: number = 0;
  winRate: number = 0;
  totalROI: number = 0;
  apiOnline: boolean = false;
  botInventory: any[] = [];
  showDocs: boolean = false;

  // Indicadores en vivo (llegados por WebSocket)
  liveRsiPrev: number = 0;
  liveEma200: number = 0;
  liveAdx: number = 0;
  liveVolumeRatio: number = 0;

  // Entradas DCA individuales: [{price: number, quantity: number}]
  dcaEntries: {price: number, quantity: number}[] = [];

  // AI State
  showAiModal: boolean = false;
  aiLoading: boolean = false;
  aiAnalysis: string = '';
  aiError: string = '';
  
  tradesPage: number = 1;
  tradesPageSize: number = 10;
  totalTrades: number = 0;

  filters = { side: '', trade_type: '', status: '', startDate: '', endDate: '' };
  private chart: any;
  private refreshSub?: Subscription;
  private wsSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private wsService: WebsocketService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  askAI() {
    if (!this.status || !this.priceLogs[0]) return;

    this.showAiModal = true;
    this.aiLoading = true;
    this.aiError = '';
    this.aiAnalysis = '';

    const aiRequest = {
      symbol: this.status.symbol || 'SOLUSDT',
      price: this.priceLogs[0].price,
      rsi: this.priceLogs[0].rsi,
      tp: this.status.target_take_profit || 0,
      sl: this.status.target_stop_loss || 0,
      trade_type: this.status.trade_type || 'NONE',
      timeframe: '1h',
      leverage: this.status.leverage || 5,
      atr_multiplier: 2.0
    };

    this.apiService.analyzeWithAI(aiRequest).subscribe({
      next: (res) => {
        this.aiAnalysis = res.analysis;
        this.aiLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.aiError = err.error?.detail || 'Error al conectar con la IA de DeepSeek.';
        this.aiLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  get currentPrice(): number {
    return this.priceLogs[0]?.price || 0;
  }

  // PnL no realizado total: suma de (precio_actual - precio_entrada) * cantidad de cada entrada DCA
  get unrealizedPnL(): number | null {
    if (!this.status.has_position || !this.currentPrice) return null;
    // Si tenemos el detalle de entradas, lo calculamos con precision
    if (this.dcaEntries.length > 0) {
      const total = this.dcaEntries.reduce((acc, e) => {
        return acc + (this.currentPrice - e.price) * e.quantity;
      }, 0);
      return total;
    }
    // Fallback: usar precio promedio y asumir cantidad de dca_count
    if (!this.status.last_buy_price) return null;
    const avg = parseFloat(this.status.last_buy_price);
    return (this.currentPrice - avg) * this.dcaCount;
  }

  // Porcentaje de progreso hacia el TP desde el precio de entrada
  get tpProgress(): number {
    if (!this.status.has_position || !this.status.last_buy_price || !this.status.target_take_profit || !this.currentPrice) return 0;
    const avg = parseFloat(this.status.last_buy_price);
    const tp = parseFloat(this.status.target_take_profit);
    const sl = parseFloat(this.status.target_stop_loss || avg);
    const totalRange = Math.abs(tp - sl);
    if (totalRange === 0) return 0;
    const progress = Math.abs(this.currentPrice - avg);
    return Math.min(100, Math.max(0, (progress / totalRange) * 100));
  }

  // Etiqueta de RSI con estado
  get rsiLabel(): string {
    const rsi = this.priceLogs[0]?.rsi || 0;
    if (rsi < 30) return 'OVERSOLD';
    if (rsi > 68) return 'OVERBOUGHT';
    return 'NEUTRAL';
  }

  get rsiLabelColor(): string {
    const rsi = this.priceLogs[0]?.rsi || 0;
    if (rsi < 30) return 'var(--success)';
    if (rsi > 68) return 'var(--danger)';
    return 'var(--text-muted)';
  }

  // Precio por encima o por debajo de la EMA200
  get priceVsEma(): string {
    if (!this.liveEma200 || !this.currentPrice) return '---';
    return this.currentPrice > this.liveEma200 ? 'ABOVE EMA' : 'BELOW EMA';
  }

  get priceVsEmaColor(): string {
    if (!this.liveEma200 || !this.currentPrice) return 'var(--text-muted)';
    return this.currentPrice > this.liveEma200 ? 'var(--success)' : 'var(--danger)';
  }

  // Numero de entradas DCA activas
  get dcaCount(): number {
    return parseInt(this.status.dca_count || '0');
  }

  // Maximo de entradas (enviado por el bot)
  get maxDca(): number {
    return parseInt(this.status.max_dca_orders || '3');
  }

  get tpDistance() {
    if (!this.status.has_position || !this.status.target_take_profit || !this.currentPrice) return null;
    const isLong = this.status.trade_type === 'LONG';
    const diff = isLong ? (this.status.target_take_profit - this.currentPrice) : (this.currentPrice - this.status.target_take_profit);
    const pct = (diff / this.currentPrice) * 100;
    return { diff, pct };
  }

  get slDistance() {
    if (!this.status.has_position || !this.status.target_stop_loss || !this.currentPrice) return null;
    const isLong = this.status.trade_type === 'LONG';
    const diff = isLong ? (this.currentPrice - this.status.target_stop_loss) : (this.status.target_stop_loss - this.currentPrice);
    const pct = (diff / this.currentPrice) * 100;
    return { diff, pct };
  }

  get filteredTrades(): Trade[] {
    return this.trades.filter(t => {
      const matchSide = !this.filters.side || t.side.toLowerCase().includes(this.filters.side.toLowerCase());
      const matchType = !this.filters.trade_type || t.trade_type.toLowerCase().includes(this.filters.trade_type.toLowerCase());
      const matchStatus = !this.filters.status || (t.message || 'SUCCESS').toLowerCase().includes(this.filters.status.toLowerCase());
      return matchSide && matchType && matchStatus;
    });
  }

  goToHistory() {
    this.router.navigate(['/history/rsi']);
  }

  goToStats() {
    this.router.navigate(['/statistics']);
  }

  ngOnInit() {
    this.fetchData();
    this.refreshSub = interval(60000).subscribe(() => this.fetchData());
    
    this.wsSub = this.wsService.getMessages().subscribe(msg => {
      this.handleWsMessage(msg);
    });
  }

  ngAfterViewInit() {
    this.initChart();
  }

  handleWsMessage(msg: any) {
    const { type, data } = msg;

    if (type === 'PRICE_UPDATE') {
      const newLog: PriceLog = {
        symbol: data.symbol,
        price: parseFloat(data.price),
        rsi: parseFloat(data.rsi),
        timestamp: data.timestamp || new Date().toISOString()
      };
      this.priceLogs.unshift(newLog);
      if (this.priceLogs.length > 50) this.priceLogs.pop();
      // Guardar indicadores adicionales si llegan en PRICE_UPDATE
      if (data.rsi_prev)     this.liveRsiPrev    = parseFloat(data.rsi_prev);
      if (data.ema200)       this.liveEma200     = parseFloat(data.ema200);
      if (data.adx)          this.liveAdx        = parseFloat(data.adx);
      if (data.volume_ratio) this.liveVolumeRatio = parseFloat(data.volume_ratio);
      this.updateChart();
    }
    else if (type === 'STATUS_UPDATE') {
      this.status = {
        ...data,
        updated_at: data.updated_at || new Date().toISOString()
      };
      // Capturar entradas DCA individuales para la tabla del portal
      if (data.dca_entries && Array.isArray(data.dca_entries)) {
        this.dcaEntries = data.dca_entries.map((e: any) => ({
          price: parseFloat(e.price),
          quantity: parseFloat(e.quantity)
        }));
      } else if (!data.has_position) {
        this.dcaEntries = [];
      }
      // Indicadores opcionales en STATUS_UPDATE
      if (data.ema200)         this.liveEma200      = parseFloat(data.ema200)      || this.liveEma200;
      if (data.adx)            this.liveAdx         = parseFloat(data.adx)         || this.liveAdx;
      if (data.volume_ratio)   this.liveVolumeRatio = parseFloat(data.volume_ratio) || this.liveVolumeRatio;
      this.updateChart();
    }
    else if (type === 'NEW_TRADE') {
      this.loadTrades(1);
      this.apiService.getBalance().subscribe(res => {
         const bals = res && res.balances ? res.balances : [];
         this.balances = bals.map((b: any) => ({
           asset: b.asset,
           free: parseFloat(b.free || '0'),
           locked: parseFloat(b.locked || '0')
         }));
      });
    }

    this.cdr.detectChanges();
  }

  initChart() {
    const ctx = document.getElementById('marketChart') as HTMLCanvasElement;
    if (!ctx) return;

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Market Price',
            data: [],
            borderColor: '#00d2ff',
            backgroundColor: 'rgba(0, 210, 255, 0.1)',
            borderWidth: 3,
            pointRadius: 0,
            fill: true,
            tension: 0.4,
            yAxisID: 'y'
          },
          {
            label: 'RSI',
            data: [],
            borderColor: '#fbbf24',
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.4,
            yAxisID: 'yRsi'
          },
          {
            label: 'Take Profit',
            data: [],
            borderColor: '#10b981',
            borderDash: [5, 5],
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            hidden: true,
            yAxisID: 'y'
          },
          {
            label: 'Stop Loss',
            data: [],
            borderColor: '#ef4444',
            borderDash: [5, 5],
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            hidden: true,
            yAxisID: 'y'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { display: false },
          y: {
            position: 'left',
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#9ca3af' }
          },
          yRsi: {
            position: 'right',
            min: 0,
            max: 100,
            grid: { display: false },
            ticks: { color: '#fbbf24', font: { size: 10 } }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
    this.updateChart();
  }

  updateChart() {
    if (!this.chart || this.priceLogs.length === 0) return;

    const displayLogs = [...this.priceLogs].reverse();
    this.chart.data.labels = displayLogs.map(l => this.formatDate(l.timestamp));
    this.chart.data.datasets[0].data = displayLogs.map(l => l.price);
    this.chart.data.datasets[1].data = displayLogs.map(l => l.rsi);

    if (this.status.has_position && this.status.target_take_profit) {
      const tp = parseFloat(this.status.target_take_profit);
      const sl = parseFloat(this.status.target_stop_loss);
      this.chart.data.datasets[2].data = displayLogs.map(() => tp);
      this.chart.data.datasets[3].data = displayLogs.map(() => sl);
      this.chart.data.datasets[2].hidden = false;
      this.chart.data.datasets[3].hidden = false;
    } else {
      this.chart.data.datasets[2].hidden = true;
      this.chart.data.datasets[3].hidden = true;
    }

    this.chart.update('none');
    this.cdr.detectChanges();
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
    this.wsSub?.unsubscribe();
  }

  fetchData() {
    this.apiService.getBotStatus().subscribe({
      next: (data: any) => {
        this.status = data || { has_position: false, last_buy_price: 0 };
        this.apiOnline = true;
        this.updateChart();
        this.cdr.detectChanges();
      },
      error: () => { 
        this.apiOnline = false; 
        this.cdr.detectChanges(); 
      }
    });

    this.loadTrades(1);

    this.apiService.getBalance().subscribe({
      next: (data: any) => {
        const bals = data && data.balances ? data.balances : [];
        this.balances = bals.map((b: any) => ({
          asset: b.asset,
          free: parseFloat(b.free || '0'),
          locked: parseFloat(b.locked || '0')
        }));
        this.cdr.detectChanges();
      }
    });
  }

  loadTrades(page: number) {
    this.tradesPage = page;
    const skip = (page - 1) * this.tradesPageSize;
    this.apiService.getTrades(skip, this.tradesPageSize, 'executed', this.filters.startDate, this.filters.endDate).subscribe({
      next: (data: any) => {
        this.totalTrades = data.total || 0;
        this.trades = data.trades || [];
        this.calculatePerformance();
        this.calculateBotInventory();
        this.cdr.detectChanges();
      }
    });
  }

  goToCancelled() {
    this.router.navigate(['/trades/cancelled']);
  }

  get totalPagesTrades(): number {
    return Math.ceil(this.totalTrades / this.tradesPageSize) || 1;
  }

  calculatePerformance() {
    const sellTrades = this.trades.filter(t => t.side === 'SELL' && t.pnl !== null);
    this.totalPnL = sellTrades.reduce((acc, curr) => acc + (parseFloat(curr.pnl) || 0), 0);
    
    const totalInvestment = sellTrades.reduce((acc, curr) => acc + (parseFloat(curr.price) * parseFloat(curr.quantity)), 0);
    this.totalROI = totalInvestment > 0 ? (this.totalPnL / totalInvestment) * 100 : 0;

    if (sellTrades.length > 0) {
      const wins = sellTrades.filter(t => (parseFloat(t.pnl) || 0) > 0).length;
      this.winRate = (wins / sellTrades.length) * 100;
    } else {
      this.winRate = 0;
    }
  }

  calculateBotInventory() {
    const inventory: { [key: string]: number } = {};
    const sortedTrades = [...this.trades].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    
    sortedTrades.forEach(trade => {
      const qty = parseFloat(trade.quantity) || 0;
      if (trade.side === 'BUY') {
        inventory[trade.symbol] = (inventory[trade.symbol] || 0) + qty;
      } else if (trade.side === 'SELL') {
        inventory[trade.symbol] = (inventory[trade.symbol] || 0) - qty;
      }
    });

    this.botInventory = Object.keys(inventory).map(symbol => ({
      symbol,
      displayQuantity: inventory[symbol].toFixed(4),
      quantity: inventory[symbol]
    })).filter(item => item.quantity > 0.0001);
  }

  formatPrice(price: any): string { 
    const p = parseFloat(price);
    return isNaN(p) ? '0.0000' : p.toFixed(4); 
  }

  formatDate(dateStr: string): string {
    if (!dateStr || dateStr.includes('1970')) return '---';
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? '---' : date.toLocaleString();
  }
}
