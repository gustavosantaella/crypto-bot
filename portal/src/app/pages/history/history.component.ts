import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './history.component.html'
})
export class HistoryComponent implements OnInit {
  allPriceLogs: any[] = [];

  constructor(
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.apiService.getPriceLogs().subscribe({
      next: (data) => {
        console.log('History Price Logs raw:', data);
        const logs = Array.isArray(data) ? data : [];
        this.allPriceLogs = logs.map((p: any) => ({
          symbol: p.symbol,
          price: parseFloat(p.price || '0'),
          rsi: parseFloat(p.rsi || '0'),
          timestamp: p.timestamp
        })).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        console.log('Processed History logs:', this.allPriceLogs);
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error in HistoryComponent fetch:', err)
    });
  }

  goBack() {
    this.router.navigate(['/']);
  }

  formatPrice(price: any) { return parseFloat(price).toFixed(4); }
  formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? '---' : date.toLocaleString();
  }
}
