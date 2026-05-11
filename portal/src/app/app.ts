import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from './api.service';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit, OnDestroy {
  status: any = { has_position: false, last_buy_price: 0 };
  trades: any[] = [];
  priceLogs: any[] = [];
  allPriceLogs: any[] = [];
  balances: any[] = [];
  totalPnL: number = 0;
  winRate: number = 0;
  apiOnline: boolean = false;
  showMarketHistory: boolean = false;
  private refreshSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  toggleMarketHistory() {
    this.showMarketHistory = !this.showMarketHistory;
    this.cdr.detectChanges();
  }

  ngOnInit() {
    this.fetchData();
    // Refresh every 20 seconds
    this.refreshSub = interval(20000).subscribe(() => this.fetchData());
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
  }

  fetchData() {
    this.apiService.getBotStatus().subscribe({
      next: (data) => {
        console.log('Status data:', data);
        this.status = data || { has_position: false, last_buy_price: 0 };
        this.apiOnline = true;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching status:', err);
        this.apiOnline = false;
        this.cdr.detectChanges();
      }
    });

    this.apiService.getTrades().subscribe({
      next: (data) => {
        console.log('Trades data:', data);
        this.trades = Array.isArray(data) ? data : [];
        this.calculatePerformance();
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching trades:', err)
    });

    this.apiService.getBalance().subscribe({
      next: (data) => {
        console.log('Balance data raw:', data);
        const bals = data && data.balances ? data.balances : [];
        this.balances = bals.map((b: any) => ({
          asset: b.asset,
          free: parseFloat(b.free || '0'),
          locked: parseFloat(b.locked || '0')
        }));
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching balance:', err)
    });

    this.apiService.getPriceLogs().subscribe({
      next: (data) => {
        console.log('Price logs raw:', data);
        const logs = Array.isArray(data) ? data : [];
        const formattedLogs = logs.map((p: any) => ({
          symbol: p.symbol,
          price: parseFloat(p.price || '0'),
          rsi: parseFloat(p.rsi || '0'),
          timestamp: p.timestamp
        }));
        this.priceLogs = formattedLogs.slice(0, 10);
        this.allPriceLogs = formattedLogs; // Store all for history
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching prices:', err)
    });
  }

  calculatePerformance() {
    try {
      const sellTrades = this.trades.filter(t => t.side === 'SELL' && t.pnl !== null && t.pnl !== undefined);
      this.totalPnL = sellTrades.reduce((acc, curr) => acc + (parseFloat(curr.pnl) || 0), 0);
      
      if (sellTrades.length > 0) {
        const wins = sellTrades.filter(t => (parseFloat(t.pnl) || 0) > 0).length;
        this.winRate = (wins / sellTrades.length) * 100;
      } else {
        this.winRate = 0;
      }
    } catch (e) {
      console.error('Error calculating performance:', e);
    }
  }

  formatPrice(price: any) {
    return parseFloat(price).toFixed(4);
  }

  formatDate(dateStr: string) {
    if (!dateStr || dateStr.includes('1970') || dateStr.includes('2026-01-01')) return '---';
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? '---' : date.toLocaleString();
  }
}
