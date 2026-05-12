import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { MetricCard } from '../../components/metric-card';

@Component({
  selector: 'app-statistics',
  standalone: true,
  imports: [CommonModule, FormsModule, MetricCard],
  templateUrl: './statistics.html'
})
export class StatisticsComponent implements OnInit {
  public Math = Math;
  trades: any[] = [];
  
  stats = {
    totalPnL: 0,
    winRate: 0,
    totalTrades: 0,
    longPnL: 0,
    shortPnL: 0,
    bestTrade: 0,
    worstTrade: 0,
    avgWin: 0,
    avgLoss: 0,
    totalVolume: 0,
    totalFees: 0 // Estimated
  };

  constructor(
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadAllTrades();
  }

  loadAllTrades() {
    // Fetch a large enough number of trades to calculate stats
    this.apiService.getTrades(0, 1000, 'executed').subscribe({
      next: (data) => {
        this.trades = data.trades || [];
        this.calculateStats();
        this.cdr.detectChanges();
      }
    });
  }

  calculateStats() {
    const sellTrades = this.trades.filter(t => t.side === 'SELL' && t.pnl !== null);
    if (sellTrades.length === 0) return;

    let totalPnL = 0;
    let wins = 0;
    let totalWinPnL = 0;
    let totalLossPnL = 0;
    let longPnL = 0;
    let shortPnL = 0;
    let maxPnL = -Infinity;
    let minPnL = Infinity;
    let totalVolume = 0;

    sellTrades.forEach(t => {
      const pnl = parseFloat(t.pnl);
      const investment = parseFloat(t.price) * parseFloat(t.quantity);
      
      totalPnL += pnl;
      totalVolume += investment;

      if (pnl > 0) {
        wins++;
        totalWinPnL += pnl;
      } else {
        totalLossPnL += pnl;
      }

      if (t.trade_type === 'LONG') longPnL += pnl;
      else shortPnL += pnl;

      if (pnl > maxPnL) maxPnL = pnl;
      if (pnl < minPnL) minPnL = pnl;
    });

    this.stats = {
      totalPnL,
      winRate: (wins / sellTrades.length) * 100,
      totalTrades: sellTrades.length,
      longPnL,
      shortPnL,
      bestTrade: maxPnL === -Infinity ? 0 : maxPnL,
      worstTrade: minPnL === Infinity ? 0 : minPnL,
      avgWin: wins > 0 ? totalWinPnL / wins : 0,
      avgLoss: (sellTrades.length - wins) > 0 ? totalLossPnL / (sellTrades.length - wins) : 0,
      totalVolume,
      totalFees: totalVolume * 0.0004 // 0.04% average taker fee
    };
  }

  goBack() {
    this.router.navigate(['/']);
  }

  formatPrice(price: any) { return parseFloat(price).toFixed(2); }
}
