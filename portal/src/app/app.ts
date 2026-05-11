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
    this.apiService.getTrades().subscribe(data => this.trades = data);
    this.apiService.getBalance().subscribe(data => this.balances = data.balances);
    this.apiService.getPriceLogs().subscribe(data => {
      this.priceLogs = data.slice(0, 10); // Last 10 prices
    });
  }

  formatPrice(price: any) {
    return parseFloat(price).toFixed(4);
  }

  formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleString();
  }
}
