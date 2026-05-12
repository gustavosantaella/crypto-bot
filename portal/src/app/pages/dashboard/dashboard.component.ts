import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { WebsocketService } from '../../websocket.service';
import { interval, Subscription } from 'rxjs';
import { MetricCard } from '../../components/metric-card';
import { AssetCard } from '../../components/asset-card';

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
  imports: [CommonModule, FormsModule, MetricCard, AssetCard],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit, OnDestroy {
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
  
  tradesPage: number = 1;
  tradesPageSize: number = 10;
  totalTrades: number = 0;

  filters = { side: '', trade_type: '', status: '', startDate: '', endDate: '' };
  private refreshSub?: Subscription;
  private wsSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private wsService: WebsocketService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  get currentPrice(): number {
    return this.priceLogs[0]?.price || 0;
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
    } 
    else if (type === 'STATUS_UPDATE') {
      this.status = {
        ...data,
        updated_at: data.updated_at || new Date().toISOString()
      };
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

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
    this.wsSub?.unsubscribe();
  }

  fetchData() {
    this.apiService.getBotStatus().subscribe({
      next: (data: any) => {
        this.status = data || { has_position: false, last_buy_price: 0 };
        this.apiOnline = true;
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
