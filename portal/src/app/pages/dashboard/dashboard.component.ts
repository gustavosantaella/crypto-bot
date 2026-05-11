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
  
  filters = { side: '', trade_type: '', status: '' };
  private refreshSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  get filteredTrades() {
    return this.trades.filter(t => {
      const matchSide = !this.filters.side || t.side.toLowerCase().includes(this.filters.side.toLowerCase());
      const matchType = !this.filters.trade_type || t.trade_type.toLowerCase().includes(this.filters.trade_type.toLowerCase());
      const statusText = t.message ? 'CANCELLED' : 'EXECUTED';
      const matchStatus = !this.filters.status || statusText.toLowerCase().includes(this.filters.status.toLowerCase());
      return matchSide && matchType && matchStatus;
    });
  }

  goToHistory() {
    this.router.navigate(['/history/rsi']);
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

    this.apiService.getTrades().subscribe({
      next: (data) => {
        const rawTrades = Array.isArray(data) ? data : [];
        this.trades = rawTrades.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        this.calculatePerformance();
        this.calculateBotInventory();
        this.cdr.detectChanges();
      }
    });

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

    this.apiService.getPriceLogs().subscribe({
      next: (data) => {
        const logs = Array.isArray(data) ? data : [];
        this.priceLogs = logs.map((p: any) => ({
          symbol: p.symbol,
          price: parseFloat(p.price || '0'),
          rsi: parseFloat(p.rsi || '0'),
          timestamp: p.timestamp
        })).slice(0, 10);
        this.cdr.detectChanges();
      }
    });
  }

  calculatePerformance() {
    const sellTrades = this.trades.filter(t => t.side === 'SELL' && t.pnl !== null);
    this.totalPnL = sellTrades.reduce((acc, curr) => acc + (parseFloat(curr.pnl) || 0), 0);
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
