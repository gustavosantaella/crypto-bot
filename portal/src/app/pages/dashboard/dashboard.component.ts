import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { interval, Subscription } from 'rxjs';
import { MetricCard } from '../../components/metric-card';
import { AssetCard } from '../../components/asset-card';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MetricCard, AssetCard],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit, OnDestroy {
  status: any = { has_position: false, last_buy_price: 0 };
  trades: any[] = [];
  priceLogs: any[] = [];
  balances: any[] = [];
  totalPnL: number = 0;
  winRate: number = 0;
  apiOnline: boolean = false;
  botInventory: any[] = [];
  showDocs: boolean = false;
  
  tradesPage: number = 1;
  tradesPageSize: number = 10;
  totalTrades: number = 0;

  filters = { side: '', trade_type: '', status: '', startDate: '', endDate: '' };
  private refreshSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  get filteredTrades() {
    // Note: Most filtering is now backend-side for performance
    return this.trades.filter(t => {
      const matchSide = !this.filters.side || t.side.toLowerCase().includes(this.filters.side.toLowerCase());
      const matchType = !this.filters.trade_type || t.trade_type.toLowerCase().includes(this.filters.trade_type.toLowerCase());
      return matchSide && matchType;
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
    this.refreshSub = interval(20000).subscribe(() => this.fetchData());
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
  }

  fetchData() {
    this.apiService.getBotStatus().subscribe({
      next: (data) => {
        this.status = data || { has_position: false, last_buy_price: 0 };
        this.apiOnline = true;
        this.cdr.detectChanges();
      },
      error: () => { this.apiOnline = false; this.cdr.detectChanges(); }
    });

    this.loadTrades(1);

    this.apiService.getBalance().subscribe({
      next: (data) => {
        const bals = data && data.balances ? data.balances : [];
        this.balances = bals.map((b: any) => ({
          asset: b.asset,
          free: parseFloat(b.free || '0'),
          locked: parseFloat(b.locked || '0')
        }));
        this.cdr.detectChanges();
      }
    });

    this.apiService.getPriceLogs(0, 10).subscribe({
      next: (data) => {
        const logs = data && data.logs ? data.logs : [];
        this.priceLogs = logs.map((p: any) => ({
          symbol: p.symbol,
          price: parseFloat(p.price || '0'),
          rsi: parseFloat(p.rsi || '0'),
          timestamp: p.timestamp
        }));
        this.cdr.detectChanges();
      }
    });
  }

  loadTrades(page: number) {
    this.tradesPage = page;
    const skip = (page - 1) * this.tradesPageSize;
    this.apiService.getTrades(skip, this.tradesPageSize, 'executed', this.filters.startDate, this.filters.endDate).subscribe({
      next: (data) => {
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

  get totalPagesTrades() {
    return Math.ceil(this.totalTrades / this.tradesPageSize);
  }

  totalROI: number = 0;

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
      if (trade.side === 'BUY') inventory[trade.symbol] = (inventory[trade.symbol] || 0) + parseFloat(trade.quantity);
      else if (trade.side === 'SELL') inventory[trade.symbol] = (inventory[trade.symbol] || 0) - parseFloat(trade.quantity);
    });
    this.botInventory = Object.keys(inventory).map(symbol => ({
      symbol,
      displayQuantity: inventory[symbol].toFixed(4),
      quantity: inventory[symbol]
    })).filter(item => item.quantity > 0.0001);
  }

  formatPrice(price: any) { return parseFloat(price).toFixed(4); }
  formatDate(dateStr: string) {
    if (!dateStr || dateStr.includes('1970')) return '---';
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? '---' : date.toLocaleString();
  }
}
