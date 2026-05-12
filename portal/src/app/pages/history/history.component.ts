import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { WebsocketService } from '../../websocket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './history.component.html'
})
export class HistoryComponent implements OnInit, OnDestroy {
  allPriceLogs: any[] = [];
  currentPage: number = 1;
  pageSize: number = 15;
  totalLogs: number = 0;
  startDate: string = '';
  endDate: string = '';
  private wsSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private wsService: WebsocketService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.wsSub = this.wsService.getMessages().subscribe(msg => {
      if (msg.type === 'PRICE_UPDATE') {
        const data = msg.data;
        const newLog = {
          symbol: data.symbol,
          price: parseFloat(data.price || '0'),
          rsi: parseFloat(data.rsi || '0'),
          timestamp: data.timestamp || new Date().toISOString()
        };
        this.allPriceLogs.unshift(newLog);
        if (this.allPriceLogs.length > 200) this.allPriceLogs.pop(); // Mantener un límite razonable en memoria
        this.totalLogs = this.allPriceLogs.length;
        this.cdr.detectChanges();
      }
    });
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  loadPage(page: number) {
    this.currentPage = page;
    // Ya no se requiere carga desde API, la lista se mantiene en memoria
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
