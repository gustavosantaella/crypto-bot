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
  currentPage: number = 1;
  pageSize: number = 15;
  totalLogs: number = 0;
  startDate: string = '';
  endDate: string = '';

  constructor(
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadPage(1);
  }

  loadPage(page: number) {
    this.currentPage = page;
    const skip = (page - 1) * this.pageSize;
    
    this.apiService.getPriceLogs(skip, this.pageSize, this.startDate, this.endDate).subscribe({
      next: (data) => {
        console.log('History Price Logs raw:', data);
        this.totalLogs = data.total || 0;
        const logs = data.logs || [];
        
        this.allPriceLogs = logs.map((p: any) => ({
          symbol: p.symbol,
          price: parseFloat(p.price || '0'),
          rsi: parseFloat(p.rsi || '0'),
          timestamp: p.timestamp
        }));
        // Note: Backend already returns them sorted by timestamp desc
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error in HistoryComponent fetch:', err)
    });
  }

  get totalPages() {
    return Math.ceil(this.totalLogs / this.pageSize);
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
