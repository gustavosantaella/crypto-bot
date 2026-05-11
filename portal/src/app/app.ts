import { Component, OnInit, OnDestroy } from '@angular/core';
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
  balances: any[] = [];
  totalPnL: number = 0;
  winRate: number = 0;
  private refreshSub?: Subscription;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.fetchData();
    // Refresh every 20 seconds
    this.refreshSub = interval(20000).subscribe(() => this.fetchData());
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
  }

  fetchData() {
    this.apiService.getBotStatus().subscribe(data => this.status = data);
    this.apiService.getTrades().subscribe(data => {
      this.trades = data;
      this.calculatePerformance();
    });
    this.apiService.getBalance().subscribe(data => {
      console.log('Balance data received:', data);
      this.balances = data.balances;
    });
    this.apiService.getPriceLogs().subscribe(data => {
      this.priceLogs = data.slice(0, 10); // Last 10 prices
    });
  }

  calculatePerformance() {
    const sellTrades = this.trades.filter(t => t.side === 'SELL' && t.pnl !== null);
    this.totalPnL = sellTrades.reduce((acc, curr) => acc + parseFloat(curr.pnl), 0);
    
    if (sellTrades.length > 0) {
      const wins = sellTrades.filter(t => parseFloat(t.pnl) > 0).length;
      this.winRate = (wins / sellTrades.length) * 100;
    } else {
      this.winRate = 0;
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
