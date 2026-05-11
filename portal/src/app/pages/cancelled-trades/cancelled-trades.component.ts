import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';

@Component({
  selector: 'app-cancelled-trades',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cancelled-trades.component.html'
})
export class CancelledTradesComponent implements OnInit {
  trades: any[] = [];
  currentPage: number = 1;
  pageSize: number = 15;
  totalTrades: number = 0;
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
    this.apiService.getTrades(skip, this.pageSize, 'cancelled', this.startDate, this.endDate).subscribe({
      next: (data) => {
        this.totalTrades = data.total || 0;
        this.trades = data.trades || [];
        this.cdr.detectChanges();
      }
    });
  }

  get totalPages() {
    return Math.ceil(this.totalTrades / this.pageSize);
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
